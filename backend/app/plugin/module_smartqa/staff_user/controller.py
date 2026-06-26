"""客服账号管理控制器。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, get_current_user

from .schema import StaffUserBindSchema, StaffUserListSchema, StaffUserSeedSchema
from .service import StaffUserService

router = APIRouter(prefix="/staff-users", tags=["SmartQA - 客服账号"])


@router.post("/seed", summary="批量初始化客服账号", response_model=ResponseSchema[dict])
async def seed_staff_users(
    data: StaffUserSeedSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """从dim_staff批量创建客服登录账号。"""
    service = StaffUserService(auth)
    result = await service.seed_staff_users(session, data.force)
    return SuccessResponse(data=result, msg="初始化成功")


@router.post("/bind", summary="绑定客服到系统用户", response_model=ResponseSchema[dict])
async def bind_user(
    data: StaffUserBindSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """手动绑定客服到系统用户。"""
    service = StaffUserService(auth)
    staff = await service.bind_user(session, data.staff_id, data.user_id)
    return SuccessResponse(data={"staff_id": staff.id, "sys_user_id": staff.sys_user_id}, msg="绑定成功")


@router.post("/{staff_id}/unbind", summary="解绑客服用户", response_model=ResponseSchema[dict])
async def unbind_user(
    staff_id: int,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """解绑客服的系统用户。"""
    service = StaffUserService(auth)
    staff = await service.unbind_user(session, staff_id)
    return SuccessResponse(data={"staff_id": staff.id, "message": "解绑成功"}, msg="解绑成功")


@router.get("", summary="获取客服账号列表", response_model=ResponseSchema[list[StaffUserListSchema]])
async def list_staff_users(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    bound_only: bool = Query(False, description="只返回已绑定的客服"),
):
    """获取客服账号列表。"""
    service = StaffUserService(auth)
    staff_users = await service.list_staff_users(session, bound_only)
    return SuccessResponse(data=[StaffUserListSchema.model_validate(s) for s in staff_users], msg="查询成功")
