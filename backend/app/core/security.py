from datetime import datetime

import jwt
from fastapi import Form, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param

from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import CustomException


class BearerTokenAuth(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != settings.TOKEN_TYPE.lower():
            if self.auto_error:
                raise CustomException(msg="认证失败，请登录后再试", code=10401, status_code=401)
            return None
        return token


class PasswordLoginForm(OAuth2PasswordRequestForm):
    def __init__(
        self,
        grant_type: str | None = Form(default=None, pattern="password"),
        scope: str = Form(default=""),
        client_id: str | None = Form(default=None),
        client_secret: str | None = Form(default=None),
        username: str = Form(),
        password: str = Form(),
        login_type: str | None = Form(default="PC端", description="PC端 | 移动端"),
    ) -> None:
        super().__init__(
            grant_type=grant_type,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
        )
        self.login_type = login_type


TokenAuthSchema = BearerTokenAuth(tokenUrl="system/auth/login", description="认证")
CustomOAuth2PasswordRequestForm = PasswordLoginForm


def create_access_token(payload: JWTPayloadSchema) -> str:
    payload_dict = payload.model_dump(exclude_none=False)
    if isinstance(payload_dict.get("exp"), datetime):
        payload_dict["exp"] = int(payload_dict["exp"].timestamp())
    return jwt.encode(payload=payload_dict, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> JWTPayloadSchema:
    if not token:
        raise CustomException(msg="认证不存在，请重新登录", code=10401, status_code=401)

    try:
        payload = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if not payload.get("sub"):
            raise CustomException(msg="无效认证，请重新登录", code=10401, status_code=401)
        return JWTPayloadSchema(**payload)
    except (jwt.InvalidSignatureError, jwt.DecodeError):
        raise CustomException(msg="无效认证，请重新登录", code=10401, status_code=401)
    except jwt.ExpiredSignatureError:
        raise CustomException(msg="认证已过期，请重新登录", code=10401, status_code=401)
    except jwt.InvalidTokenError:
        raise CustomException(msg="token 已失效，请重新登录", code=10401, status_code=401)
