from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from app.common.enums import PermissionFilterStrategy
from app.core.base_schema import AuthSchema


class Permission:
    """Minimal data permission filter for SmartQA P0."""

    DATA_SCOPE_SELF = 1
    DATA_SCOPE_ALL = 4

    def __init__(self, model: Any, auth: AuthSchema) -> None:
        self.model = model
        self.auth = auth

    async def filter_query(self, query: Any) -> Any:
        condition = await self.__permission_condition()
        return query.where(condition) if condition is not None else query

    async def __permission_condition(self) -> ColumnElement | None:
        if not self.auth.user or not self.auth.check_data_scope:
            return None
        if self.auth.user.is_superuser:
            return None

        strategy = getattr(
            self.model,
            "__permission_strategy__",
            PermissionFilterStrategy.DATA_SCOPE,
        )
        if strategy == PermissionFilterStrategy.MENU_AUTH:
            return await self.__filter_by_menu_auth()
        if strategy == PermissionFilterStrategy.OWN:
            return self.__filter_by_own()
        if strategy == PermissionFilterStrategy.USER_BINDING:
            return self.__filter_by_user_binding()
        return self.__filter_by_data_scope()

    async def __filter_by_menu_auth(self) -> ColumnElement | None:
        roles = getattr(self.auth.user, "roles", []) or []
        menu_ids = {
            menu.id
            for role in roles
            for menu in (getattr(role, "menus", []) or [])
            if menu.status == 0
        }
        id_attr = getattr(self.model, "id", None)
        if id_attr is None:
            return None
        return id_attr.in_(list(menu_ids)) if menu_ids else id_attr == -1

    def __filter_by_user_binding(self) -> ColumnElement | None:
        roles = getattr(self.auth.user, "roles", []) or []
        role_ids = [role.id for role in roles]
        id_attr = getattr(self.model, "id", None)
        if id_attr is None:
            return None
        return id_attr.in_(role_ids) if role_ids else id_attr == -1

    def __filter_by_own(self) -> ColumnElement | None:
        created_id_attr = getattr(self.model, "created_id", None)
        if created_id_attr is not None and self.auth.user:
            return created_id_attr == self.auth.user.id
        return None

    def __filter_by_data_scope(self) -> ColumnElement | None:
        if not hasattr(self.model, "created_id"):
            return None

        roles = getattr(self.auth.user, "roles", []) or []
        data_scopes = {getattr(role, "data_scope", self.DATA_SCOPE_SELF) for role in roles}
        if self.DATA_SCOPE_ALL in data_scopes:
            return None
        return self.__filter_by_own()
