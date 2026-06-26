import json
import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, NewType

import ua_parser
from fastapi import BackgroundTasks, Request
from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_platform.tenant.model import TenantModel
from app.api.v1.module_system.user.crud import UserCRUD
from app.api.v1.module_system.user.model import UserModel
from app.common.enums import RedisInitKeyConfig
from app.config.setting import settings
from app.core.base_schema import (
    AuthSchema,
    JWTOutSchema,
    JWTPayloadSchema,
    LogoutPayloadSchema,
    RefreshTokenPayloadSchema,
)
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.redis_crud import RedisCURD
from app.core.request_context import RequestContext
from app.core.security import CustomOAuth2PasswordRequestForm, create_access_token, decode_access_token
from app.utils.captcha_util import CaptchaUtil
from app.utils.common_util import get_random_character
from app.utils.hash_bcrpy_util import PwdUtil
from app.utils.ip_local_util import IpLocalUtil, get_client_ip

from .schema import (
    CaptchaOutSchema,
    LoginOutSchema,
    OnlineOutSchema,
)

CaptchaKey = NewType("CaptchaKey", str)
CaptchaBase64 = NewType("CaptchaBase64", str)


async def _write_login_log(
    username: str,
    status: int,
    login_ip: str | None = None,
    login_location: str | None = None,
    request_os: str | None = None,
    request_browser: str | None = None,
    msg: str | None = None,
) -> int | None:
    return None


async def _async_fill_login_location(redis: Redis, login_log_id: int, ip: str | None) -> None:
    return None


def _resolve_request_ip(request: Request) -> str | None:
    return get_client_ip(request)


def _loads_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    return {}


class LoginService:
    def __init__(self, auth: AuthSchema | None = None) -> None:
        self.auth = auth

    @classmethod
    async def authenticate_user(
        cls,
        request: Request,
        background_tasks: BackgroundTasks,
        redis: Redis,
        login_form: CustomOAuth2PasswordRequestForm,
        db: AsyncSession,
    ) -> LoginOutSchema:
        ua_result = ua_parser.parse(request.headers.get("user-agent"))
        request_ip = _resolve_request_ip(request)
        login_location = await IpLocalUtil.resolve_location_for_log(redis, request_ip)
        login_os = ua_result.os.family if ua_result.os else "Unknown"
        login_browser = ua_result.user_agent.family if ua_result.user_agent else "Unknown"

        referer = request.headers.get("referer", "")
        request_from_docs = referer.endswith(("docs", "redoc"))

        if settings.CAPTCHA_ENABLE and not request_from_docs:
            if not login_form.captcha_key or not login_form.captcha:
                raise CustomException(msg="验证码不能为空")
            await CaptchaService.check_captcha(
                redis=redis,
                key=login_form.captcha_key,
                captcha=login_form.captcha,
            )

        auth = AuthSchema(db=db, check_data_scope=False)
        user = await UserCRUD(auth).get(username=login_form.username)
        if not user:
            await _write_login_log(
                username=login_form.username,
                status=2,
                login_ip=request_ip,
                login_location=login_location,
                request_os=login_os,
                request_browser=login_browser,
                msg="用户不存在",
            )
            raise CustomException(msg="用户不存在")

        if not PwdUtil.verify_password(plain_password=login_form.password, password_hash=user.password):
            await _write_login_log(
                username=login_form.username,
                status=2,
                login_ip=request_ip,
                login_location=login_location,
                request_os=login_os,
                request_browser=login_browser,
                msg="账号或密码错误",
            )
            raise CustomException(msg="账号或密码错误")

        if user.status == 1:
            await _write_login_log(
                username=login_form.username,
                status=2,
                login_ip=request_ip,
                login_location=login_location,
                request_os=login_os,
                request_browser=login_browser,
                msg="用户已被停用",
            )
            raise CustomException(msg="用户已被停用")

        await cls._ensure_user_tenant_enabled(db=db, user=user)
        await UserCRUD(auth).update_last_login(id=user.id)

        if not login_form.login_type:
            raise CustomException(msg="登录类型不能为空")

        token = await cls.create_token(
            request=request,
            redis=redis,
            user=user,
            login_type=login_form.login_type,
        )

        user_info = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "avatar": user.avatar,
            "is_superuser": user.is_superuser,
        }

        log_id = await _write_login_log(
            username=user.username,
            status=1,
            login_ip=request_ip,
            login_location=login_location,
            request_os=login_os,
            request_browser=login_browser,
            msg="登录成功",
        )
        if log_id and login_location == "归属地查询中":
            background_tasks.add_task(_async_fill_login_location, redis, log_id, request_ip)

        return LoginOutSchema(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_in=token.expires_in,
            token_type=token.token_type,
            user_info=user_info,
        )

    @staticmethod
    async def _ensure_user_tenant_enabled(db: AsyncSession, user: UserModel) -> None:
        stmt = (
            select(TenantModel)
            .where(
                TenantModel.id == user.tenant_id,
                TenantModel.status == 0,
                TenantModel.is_deleted.is_(False),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise CustomException(msg="所属租户已被禁用，请联系管理员")

    @classmethod
    async def create_token(cls, request: Request, redis: Redis, user: UserModel, login_type: str) -> JWTOutSchema:
        session_id = str(uuid.uuid4())
        ua_result = ua_parser.parse(request.headers.get("user-agent"))
        request_ip = _resolve_request_ip(request)
        login_location = await IpLocalUtil.resolve_location_for_log(redis, request_ip)

        request.state.ctx = replace(
            getattr(request.state, "ctx", None) or RequestContext(),
            session_id=session_id,
            user_username=user.username,
            login_location=login_location,
        )

        access_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        refresh_expires = timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS)
        now = datetime.now()

        session_info = OnlineOutSchema(
            session_id=session_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
            is_superuser=user.is_superuser,
            name=user.name,
            user_name=user.username,
            ipaddr=request_ip,
            login_location=login_location,
            os=ua_result.os.family if ua_result.os else "Unknown",
            browser=ua_result.user_agent.family if ua_result.user_agent else "Unknown",
            login_time=user.last_login,
            login_type=login_type,
        ).model_dump_json()

        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.USER_SESSION.key}:{session_id}",
            value=session_info,
            expire=int(refresh_expires.total_seconds()),
        )

        access_token = create_access_token(
            payload=JWTPayloadSchema(sub=session_id, is_refresh=False, exp=now + access_expires)
        )
        refresh_token = create_access_token(
            payload=JWTPayloadSchema(sub=session_id, is_refresh=True, exp=now + refresh_expires)
        )

        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}",
            value=access_token,
            expire=int(access_expires.total_seconds()),
        )
        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{session_id}",
            value=refresh_token,
            expire=int(refresh_expires.total_seconds()),
        )

        return JWTOutSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_expires.total_seconds()),
            token_type=settings.TOKEN_TYPE,
        )

    @classmethod
    async def refresh_token(
        cls,
        db: AsyncSession,
        redis: Redis,
        refresh_token: RefreshTokenPayloadSchema,
    ) -> JWTOutSchema:
        token_payload = decode_access_token(token=refresh_token.refresh_token)
        if not token_payload.is_refresh:
            raise CustomException(msg="非法凭证，请传入刷新令牌")

        session_id = token_payload.sub
        session_info_raw = await RedisCURD(redis).get(f"{RedisInitKeyConfig.USER_SESSION.key}:{session_id}")
        if not session_info_raw:
            raise CustomException(msg="会话已过期，请重新登录")

        session_info = _loads_json(session_info_raw)
        user_id = session_info.get("user_id")
        if not session_id or not user_id:
            raise CustomException(msg="非法凭证，无法获取会话编号或用户 ID")

        auth = AuthSchema(db=db, check_data_scope=False)
        user = await UserCRUD(auth).get(id=user_id)
        if not user:
            raise CustomException(msg="刷新 token 失败，用户不存在")
        if user.status == 1:
            raise CustomException(msg="用户已被停用")

        access_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        refresh_expires = timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS)
        now = datetime.now()

        await RedisCURD(redis).expire(
            key=f"{RedisInitKeyConfig.USER_SESSION.key}:{session_id}",
            expire=int(refresh_expires.total_seconds()),
        )

        access_token = create_access_token(
            payload=JWTPayloadSchema(sub=session_id, is_refresh=False, exp=now + access_expires)
        )
        refresh_token_new = create_access_token(
            payload=JWTPayloadSchema(sub=session_id, is_refresh=True, exp=now + refresh_expires)
        )

        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}",
            value=access_token,
            expire=int(access_expires.total_seconds()),
        )
        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{session_id}",
            value=refresh_token_new,
            expire=int(refresh_expires.total_seconds()),
        )

        return JWTOutSchema(
            access_token=access_token,
            refresh_token=refresh_token_new,
            token_type=settings.TOKEN_TYPE,
            expires_in=int(access_expires.total_seconds()),
        )

    @staticmethod
    async def logout(redis: Redis, token: LogoutPayloadSchema) -> bool:
        payload = decode_access_token(token=token.token)
        session_id = payload.sub
        if not session_id:
            raise CustomException(msg="非法凭证，无法获取会话编号")

        await RedisCURD(redis).delete(f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}")
        await RedisCURD(redis).delete(f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{session_id}")
        await RedisCURD(redis).delete(f"{RedisInitKeyConfig.USER_SESSION.key}:{session_id}")
        logger.info(f"用户退出登录成功，会话编号:{session_id}")
        return True

class CaptchaService:
    @staticmethod
    async def get_captcha(redis: Redis) -> CaptchaOutSchema:
        if not settings.CAPTCHA_ENABLE:
            raise CustomException(msg="未开启验证码服务")

        captcha_base64, captcha_value = CaptchaUtil.captcha_arithmetic()
        captcha_key = get_random_character()
        await RedisCURD(redis).set(
            key=f"{RedisInitKeyConfig.CAPTCHA_CODES.key}:{captcha_key}",
            value=captcha_value,
            expire=settings.CAPTCHA_EXPIRE_SECONDS,
        )
        return CaptchaOutSchema(
            enable=settings.CAPTCHA_ENABLE,
            key=CaptchaKey(captcha_key),
            img_base=CaptchaBase64(f"data:image/png;base64,{captcha_base64}"),
        )

    @staticmethod
    async def check_captcha(redis: Redis, key: str, captcha: str) -> bool:
        if not captcha:
            raise CustomException(msg="验证码不能为空")

        redis_key = f"{RedisInitKeyConfig.CAPTCHA_CODES.key}:{key}"
        captcha_value = await RedisCURD(redis).get(redis_key)
        if not captcha_value:
            raise CustomException(msg="验证码已过期")

        if isinstance(captcha_value, bytes):
            captcha_value = captcha_value.decode("utf-8")
        if captcha.lower() != str(captcha_value).lower():
            raise CustomException(msg="验证码错误")

        await RedisCURD(redis).delete(redis_key)
        return True
