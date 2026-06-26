from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel
from app.plugin.module_smartqa.models.dimension import DimStaffModel


async def is_smartqa_boss(auth: AuthSchema) -> bool:
    """Return whether current user has SmartQA boss-level access."""

    user = auth.user
    if not user:
        return False
    if user.is_superuser:
        return True
    if any(getattr(role, "code", None) == "smartqa_boss" for role in (getattr(user, "roles", None) or [])):
        return True
    if not auth.db or not getattr(user, "id", None):
        return False

    from app.api.v1.module_system.role.model import RoleModel
    from app.api.v1.module_system.user.model import UserRolesModel

    stmt = (
        select(RoleModel.code)
        .join(UserRolesModel, RoleModel.id == UserRolesModel.role_id)
        .where(
            UserRolesModel.user_id == user.id,
            RoleModel.code == "smartqa_boss",
            RoleModel.status == 0,
            RoleModel.is_deleted == False,  # noqa: E712
        )
        .limit(1)
    )
    result = await auth.db.execute(stmt)
    return result.scalar_one_or_none() == "smartqa_boss"


async def ensure_smartqa_boss(auth: AuthSchema) -> None:
    """Raise 403 unless current user has SmartQA boss access."""

    if not await is_smartqa_boss(auth):
        raise CustomException(msg="仅老板端可操作该功能", code=10403, status_code=403)


async def get_bound_staff_id(auth: AuthSchema) -> int | None:
    """Return staff id bound to current system user."""

    if not auth.user:
        return None
    stmt = select(DimStaffModel.id).where(
        DimStaffModel.sys_user_id == auth.user.id,
        DimStaffModel.is_deleted == False,  # noqa: E712
    )
    result = await auth.db.execute(stmt)
    return result.scalar_one_or_none()


async def build_staff_scope_condition(
    auth: AuthSchema,
    conversation_model: type[DwdQnConversationModel] = DwdQnConversationModel,
) -> ColumnElement | None:
    """老板看全量，客服只看绑定客服的数据。"""

    if await is_smartqa_boss(auth):
        return None

    staff_id = await get_bound_staff_id(auth)
    if not staff_id:
        raise CustomException(msg="当前账号未绑定客服身份，无法查看客服数据", code=10403, status_code=403)
    return conversation_model.staff_id == staff_id


async def ensure_conversation_access(
    auth: AuthSchema,
    db: AsyncSession,
    conversation: DwdQnConversationModel | None,
) -> DwdQnConversationModel:
    """Validate current user can access the conversation."""

    if not conversation:
        raise CustomException(msg="会话不存在")
    if await is_smartqa_boss(auth):
        return conversation

    staff_id = await get_bound_staff_id(auth)
    if not staff_id or conversation.staff_id != staff_id:
        raise CustomException(msg="无权查看该会话", code=10403, status_code=403)
    return conversation
