"""客服账号初始化服务。"""

import secrets
import string
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.user.model import UserModel
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_smartqa.models.dimension import DimStaffModel
from app.utils.hash_bcrpy_util import PwdUtil


class StaffUserService:
    """客服账号管理服务。"""

    def __init__(self, auth: AuthSchema):
        self.auth = auth

    async def seed_staff_users(self, session: AsyncSession, force: bool = False) -> dict:
        """从dim_staff批量初始化客服登录账号。

        Args:
            session: 数据库会话
            force: 是否强制为已绑定的客服重新创建账号

        Returns:
            初始化结果统计
        """
        stmt = select(DimStaffModel).where(
            DimStaffModel.status == "active",
            DimStaffModel.is_deleted == False,  # noqa: E712
        )

        if not force:
            stmt = stmt.where(DimStaffModel.sys_user_id.is_(None))

        result = await session.execute(stmt)
        staff_list = list(result.scalars().all())

        created_count = 0
        skipped_count = 0
        errors = []

        for staff in staff_list:
            try:
                if staff.sys_user_id and not force:
                    skipped_count += 1
                    continue

                username = self._generate_username(staff.staff_key, staff.staff_name)

                existing_user_stmt = select(UserModel).where(
                    UserModel.username == username,
                    UserModel.is_deleted == False,  # noqa: E712
                )
                existing_user_result = await session.execute(existing_user_stmt)
                existing_user = existing_user_result.scalar_one_or_none()

                if existing_user:
                    if not staff.sys_user_id:
                        staff.sys_user_id = existing_user.id
                        staff.updated_time = datetime.now()
                        created_count += 1
                    else:
                        skipped_count += 1
                    continue

                initial_password = self._generate_password()

                new_user = UserModel(
                    username=username,
                    name=staff.staff_name,
                    password=PwdUtil.hash_password(initial_password),
                    email=f"{username}@smartqa.local",
                    mobile=None,
                    avatar=None,
                    status=0,
                    is_superuser=False,
                tenant_id=self.auth.tenant_id or 1,
                created_id=self.auth.user_id,
                )
                session.add(new_user)
                await session.flush()

                staff.sys_user_id = new_user.id
                staff.updated_time = datetime.now()

                created_count += 1

            except Exception as e:
                errors.append({
                    "staff_key": staff.staff_key,
                    "staff_name": staff.staff_name,
                    "error": str(e),
                })

        await session.commit()

        return {
            "total_staff": len(staff_list),
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors,
        }

    async def bind_user(self, session: AsyncSession, staff_id: int, user_id: int) -> DimStaffModel:
        """手动绑定客服到系统用户。"""
        staff_stmt = select(DimStaffModel).where(
            DimStaffModel.id == staff_id,
            DimStaffModel.is_deleted == False,  # noqa: E712
        )
        staff_result = await session.execute(staff_stmt)
        staff = staff_result.scalar_one_or_none()
        if not staff:
            raise CustomException("客服不存在")

        user_stmt = select(UserModel).where(
            UserModel.id == user_id,
            UserModel.is_deleted == False,  # noqa: E712
        )
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise CustomException("用户不存在")

        staff.sys_user_id = user_id
        staff.updated_time = datetime.now()
        staff.updated_id = self.auth.user_id

        await session.commit()
        return staff

    async def unbind_user(self, session: AsyncSession, staff_id: int) -> DimStaffModel:
        """解绑客服的系统用户。"""
        staff_stmt = select(DimStaffModel).where(
            DimStaffModel.id == staff_id,
            DimStaffModel.is_deleted == False,  # noqa: E712
        )
        staff_result = await session.execute(staff_stmt)
        staff = staff_result.scalar_one_or_none()
        if not staff:
            raise CustomException("客服不存在")

        staff.sys_user_id = None
        staff.updated_time = datetime.now()
        staff.updated_id = self.auth.user_id

        await session.commit()
        return staff

    async def list_staff_users(self, session: AsyncSession, bound_only: bool = False) -> list[dict]:
        """获取客服账号列表。"""
        stmt = (
            select(DimStaffModel, UserModel)
            .outerjoin(UserModel, DimStaffModel.sys_user_id == UserModel.id)
            .where(DimStaffModel.is_deleted == False)  # noqa: E712
        )

        if bound_only:
            stmt = stmt.where(DimStaffModel.sys_user_id.isnot(None))

        result = await session.execute(stmt)
        rows = result.all()

        return [
            {
                "staff_id": staff.id,
                "staff_key": staff.staff_key,
                "staff_name": staff.staff_name,
                "primary_account": staff.primary_account,
                "source_system": staff.source_system,
                "status": staff.status,
                "sys_user_id": staff.sys_user_id,
                "username": user.username if user else None,
                "nickname": user.name if user else None,
                "user_status": user.status if user else None,
            }
            for staff, user in rows
        ]

    def _generate_username(self, staff_key: str, staff_name: str) -> str:
        """生成用户名：staff_开头 + staff_key后8位。"""
        return f"staff_{staff_key[-8:]}"

    def _generate_password(self, length: int = 12) -> str:
        """生成随机初始密码。"""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
