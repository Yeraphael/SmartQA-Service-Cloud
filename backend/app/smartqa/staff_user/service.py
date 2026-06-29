"""客服账号初始化服务。"""

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.user.model import UserModel, UserRolesModel
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.smartqa.models.dimension import DimStaffModel
from app.utils.hash_bcrpy_util import PwdUtil

DEFAULT_STAFF_PASSWORD = "SmartQA@123456"


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

                username = self._generate_username(staff.primary_account)

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

                new_user = UserModel(
                    username=username,
                    name=staff.staff_name,
                    password=PwdUtil.hash_password(DEFAULT_STAFF_PASSWORD),
                    email=None,
                    mobile=None,
                    avatar=None,
                    status=0,
                    is_superuser=False,
                    tenant_id=self.auth.tenant_id or 1,
                    created_id=self.auth.user.id if self.auth.user else None,
                )
                session.add(new_user)
                await session.flush()
                await self._ensure_staff_role(session, new_user.id)

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
            "default_password": DEFAULT_STAFF_PASSWORD,
        }

    async def ensure_staff_user(self, session: AsyncSession, staff_id: int, password: str = DEFAULT_STAFF_PASSWORD) -> dict:
        """为单个客服创建或补绑定系统账号。"""
        staff = await self._get_staff(session, staff_id)
        if staff.sys_user_id:
            user = await session.get(UserModel, staff.sys_user_id)
            if user:
                await self._ensure_staff_role(session, user.id)
                await session.commit()
                return {"staff_id": staff.id, "sys_user_id": user.id, "username": user.username, "created": False}

        username = self._generate_username(staff.primary_account)
        result = await session.execute(
            select(UserModel).where(
                UserModel.username == username,
                UserModel.tenant_id == (self.auth.tenant_id or 1),
                UserModel.is_deleted == False,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()
        created = False
        if not user:
            user = UserModel(
                username=username,
                name=staff.staff_name,
                password=PwdUtil.hash_password(password),
                email=None,
                mobile=None,
                avatar=None,
                status=0,
                is_superuser=False,
                tenant_id=self.auth.tenant_id or 1,
                created_id=self.auth.user.id if self.auth.user else None,
            )
            session.add(user)
            await session.flush()
            created = True

        await self._ensure_staff_role(session, user.id)
        staff.sys_user_id = user.id
        staff.updated_time = datetime.now()
        await session.commit()
        return {"staff_id": staff.id, "sys_user_id": user.id, "username": user.username, "created": created}

    async def reset_staff_password(self, session: AsyncSession, staff_id: int, password: str = DEFAULT_STAFF_PASSWORD) -> dict:
        """重置客服系统账号密码。"""
        staff = await self._get_staff(session, staff_id)
        if not staff.sys_user_id:
            raise CustomException("客服尚未绑定系统账号")
        user = await session.get(UserModel, staff.sys_user_id)
        if not user or user.is_deleted:
            raise CustomException("绑定的系统账号不存在")
        if user.is_superuser:
            raise CustomException("不能重置超级管理员密码")
        user.password = PwdUtil.hash_password(password)
        user.updated_time = datetime.now()
        user.updated_id = self.auth.user.id if self.auth.user else None
        await session.commit()
        return {"staff_id": staff.id, "sys_user_id": user.id, "username": user.username}

    async def set_staff_user_status(self, session: AsyncSession, staff_id: int, status: int) -> dict:
        """启停客服系统账号。"""
        staff = await self._get_staff(session, staff_id)
        if not staff.sys_user_id:
            raise CustomException("客服尚未绑定系统账号")
        user = await session.get(UserModel, staff.sys_user_id)
        if not user or user.is_deleted:
            raise CustomException("绑定的系统账号不存在")
        if user.is_superuser:
            raise CustomException("不能修改超级管理员状态")
        user.status = status
        user.updated_time = datetime.now()
        user.updated_id = self.auth.user.id if self.auth.user else None
        await session.commit()
        return {"staff_id": staff.id, "sys_user_id": user.id, "username": user.username, "status": user.status}

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
        await self._ensure_staff_role(session, user_id)

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

    async def _get_staff(self, session: AsyncSession, staff_id: int) -> DimStaffModel:
        result = await session.execute(
            select(DimStaffModel).where(
                DimStaffModel.id == staff_id,
                DimStaffModel.is_deleted == False,  # noqa: E712
            )
        )
        staff = result.scalar_one_or_none()
        if not staff:
            raise CustomException("客服不存在")
        return staff

    async def _ensure_staff_role(self, session: AsyncSession, user_id: int) -> None:
        result = await session.execute(
            select(RoleModel).where(
                RoleModel.code == "smartqa_staff",
                RoleModel.tenant_id == (self.auth.tenant_id or 1),
                RoleModel.is_deleted == False,  # noqa: E712
            )
        )
        role = result.scalar_one_or_none()
        if role:
            exists = await session.execute(
                select(UserRolesModel).where(
                    UserRolesModel.user_id == user_id,
                    UserRolesModel.role_id == role.id,
                )
            )
            if not exists.scalar_one_or_none():
                session.add(UserRolesModel(user_id=user_id, role_id=role.id))

    def _generate_username(self, primary_account: str) -> str:
        """生成与数据管道一致的客服登录账号。"""
        digest = hashlib.sha256(primary_account.encode("utf-8")).hexdigest()[:10]
        return f"staff_{digest}"
