from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ErrorResponse, ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.base_schema import JWTOutSchema, LogoutPayloadSchema, RefreshTokenPayloadSchema
from app.core.dependencies import db_getter, get_current_user, redis_getter
from app.core.logger import logger
from app.core.router_class import SmartQARoute
from app.core.security import CustomOAuth2PasswordRequestForm

from .schema import CaptchaOutSchema, LoginOutSchema
from .service import CaptchaService, LoginService

AuthRouter = APIRouter(route_class=SmartQARoute, prefix="/auth", tags=["系统认证"])


@AuthRouter.post("/login", summary="登录", response_model=LoginOutSchema)
async def login_for_access_token_controller(
    request: Request,
    redis: Annotated[Redis, Depends(redis_getter)],
    login_form: Annotated[CustomOAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse | LoginOutSchema:
    login_result = await LoginService.authenticate_user(
        request=request,
        redis=redis,
        login_form=login_form,
        db=db,
    )
    logger.info(f"用户 {login_form.username} 登录成功")
    if settings.DOCS_URL in request.headers.get("referer", ""):
        return login_result
    return SuccessResponse(data=login_result, msg="登录成功")


@AuthRouter.post(
    "/token/refresh",
    summary="刷新 token",
    response_model=ResponseSchema[JWTOutSchema],
)
async def get_new_token_controller(
    payload: RefreshTokenPayloadSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    new_token = await LoginService.refresh_token(db=db, redis=redis, refresh_token=payload)
    return SuccessResponse(data=new_token, msg="刷新成功")


@AuthRouter.get(
    "/captcha/get",
    summary="获取验证码",
    response_model=ResponseSchema[CaptchaOutSchema],
)
async def get_captcha_for_login_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    captcha = await CaptchaService.get_captcha(redis=redis)
    return SuccessResponse(data=captcha, msg="获取验证码成功")


@AuthRouter.post(
    "/logout",
    summary="退出登录",
    dependencies=[Depends(get_current_user)],
    response_model=ResponseSchema[None],
)
async def logout_controller(
    payload: LogoutPayloadSchema,
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    if await LoginService.logout(redis=redis, token=payload):
        return SuccessResponse(msg="退出成功")
    return ErrorResponse(msg="退出失败")
