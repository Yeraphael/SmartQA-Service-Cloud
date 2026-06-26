from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import db_getter, get_current_user
from app.core.logger import logger
from app.core.router_class import OperationLogRoute

from .schema import CurrentUserUpdateSchema, UserChangePasswordSchema, UserForgetPasswordSchema, UserOutSchema
from .service import UserService

UserRouter = APIRouter(route_class=OperationLogRoute, prefix="/user", tags=["账号"])


@UserRouter.get(
    "/current/info",
    summary="查询当前用户信息",
    response_model=ResponseSchema[UserOutSchema],
)
async def get_current_user_info_controller(
    auth: Annotated[AuthSchema, Depends(get_current_user)],
) -> JSONResponse:
    user_dict = await UserService(auth).current_info()
    return SuccessResponse(data=user_dict, msg="获取当前用户信息成功")


@UserRouter.put(
    "/current/info/update",
    summary="更新当前用户基本信息",
    response_model=ResponseSchema[UserOutSchema],
)
async def update_current_user_info_controller(
    data: CurrentUserUpdateSchema,
    auth: Annotated[AuthSchema, Depends(get_current_user)],
) -> JSONResponse:
    result_dict = await UserService(auth).update_current_info(data=data)
    return SuccessResponse(data=result_dict, msg="更新当前用户基本信息成功")


@UserRouter.put(
    "/password/change",
    summary="修改当前用户密码",
    response_model=ResponseSchema[UserOutSchema],
)
async def change_current_user_password_controller(
    data: UserChangePasswordSchema,
    auth: Annotated[AuthSchema, Depends(get_current_user)],
) -> JSONResponse:
    result_dict = await UserService(auth).change_password(data=data)
    return SuccessResponse(data=result_dict, msg="修改密码成功, 请重新登录")


@UserRouter.post(
    "/password/forget",
    summary="忘记密码",
    response_model=ResponseSchema[UserOutSchema],
)
async def forget_password_controller(
    data: UserForgetPasswordSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    auth = AuthSchema(db=db, check_data_scope=False)
    result = await UserService(auth).forget_password(data=data)
    logger.info("{} 重置密码成功", data.username)
    return SuccessResponse(data=result, msg="重置密码成功")
