from app.api.v1.module_platform.menu.crud import MenuCRUD
from app.api.v1.module_platform.menu.schema import MenuOutSchema
from app.api.v1.module_system.role.crud import RoleCRUD
from app.core.base_schema import AuthSchema, BatchSetAvailable
from app.core.exceptions import CustomException
from app.utils.common_util import traversal_to_tree
from app.utils.hash_bcrpy_util import PwdUtil

from .crud import UserCRUD
from .schema import (
    CurrentUserUpdateSchema,
    ResetPasswordSchema,
    UserChangePasswordSchema,
    UserCreateSchema,
    UserForgetPasswordSchema,
    UserOutSchema,
    UserQueryParam,
    UserRegisterSchema,
    UserUpdateSchema,
)


class UserService:
    """用户管理服务"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def detail(self, id: int) -> UserOutSchema:
        user = await UserCRUD(self.auth).get_or_404(id=id)
        return UserOutSchema.model_validate(user)

    async def get_list(
        self,
        search: UserQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[UserOutSchema]:
        user_list = await UserCRUD(self.auth).get_list(search=vars(search) if search else None, order_by=order_by)
        return [UserOutSchema.model_validate(user) for user in user_list]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: UserQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        offset = (page_no - 1) * page_size
        return await UserCRUD(self.auth).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=vars(search) if search else None,
            out_schema=UserOutSchema,
        )

    async def create(self, data: UserCreateSchema) -> UserOutSchema:
        if not data.username:
            raise CustomException(msg="用户名不能为空")
        if data.is_superuser:
            raise CustomException(msg="不允许创建超级管理员")
        user = await UserCRUD(self.auth).get(username=data.username)
        if user:
            raise CustomException(msg="已存在相同用户名称的账号")

        if data.password:
            data.password = PwdUtil.hash_password(password=data.password)
        user_dict = data.model_dump(exclude_unset=True, exclude={"role_ids"})
        new_user = await UserCRUD(self.auth).create(data=user_dict)
        if data.role_ids and len(data.role_ids) > 0:
            await UserCRUD(self.auth).set_user_roles(user_ids=[new_user.id], role_ids=data.role_ids)
        return UserOutSchema.model_validate(new_user)

    async def update(self, id: int, data: UserUpdateSchema) -> UserOutSchema:
        if not data.username:
            raise CustomException(msg="账号不能为空")

        user = await UserCRUD(self.auth).get_or_404(id=id)
        if user.is_superuser:
            raise CustomException(msg="超级管理员不允许修改")

        exist_user = await UserCRUD(self.auth).get(username=data.username)
        if exist_user and exist_user.id != id:
            raise CustomException(msg="更新失败，账号已存在")
        if data.mobile:
            exist_mobile_user = await UserCRUD(self.auth).get(mobile=data.mobile)
            if exist_mobile_user and exist_mobile_user.id != id:
                raise CustomException(msg="该数据已存在")
        if data.email:
            exist_email_user = await UserCRUD(self.auth).get(email=data.email)
            if exist_email_user and exist_email_user.id != id:
                raise CustomException(msg="该数据已存在")
        new_user = await UserCRUD(self.auth).update(id=id, data=data)

        if data.role_ids and len(data.role_ids) > 0:
            roles = await RoleCRUD(self.auth).get_list(search={"id": ("in", data.role_ids)})
            if len(roles) != len(data.role_ids):
                raise CustomException(msg="更新失败，部分角色不存在")
            if not all(role.status == 0 for role in roles):
                raise CustomException(msg="更新失败，部分角色已被禁用")
            await UserCRUD(self.auth).set_user_roles(user_ids=[id], role_ids=data.role_ids)

        return UserOutSchema.model_validate(new_user)

    async def delete(self, ids: list[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        users = await UserCRUD(self.auth).get_list(search={"id": ("in", ids)})
        user_map = {u.id: u for u in users}
        for uid in ids:
            user = user_map.get(uid)
            if not user:
                raise CustomException(msg="该数据不存在")
            if user.is_superuser:
                raise CustomException(msg="超级管理员不能删除")
            if user.status == 0:
                raise CustomException(msg="用户已启用,不能删除")
            if self.auth.user and self.auth.user.id == uid:
                raise CustomException(msg="不能删除当前登陆用户")

        await UserCRUD(self.auth).set_user_roles(user_ids=ids, role_ids=[])
        await UserCRUD(self.auth).delete(ids=ids)

    async def current_info(self) -> UserOutSchema:
        if not self.auth.user or not self.auth.user.id:
            raise CustomException(msg="该数据不存在")
        user = await UserCRUD(self.auth).get(id=self.auth.user.id)
        user_dict = UserOutSchema.model_validate(user)

        _pc_only = {"client": "pc"}
        if self.auth.user and self.auth.user.is_superuser:
            menu_all = await MenuCRUD(self.auth).tree_list(
                search={"type": ("in", [1, 2, 3, 4]), "status": 0, **_pc_only},
                order_by=[{"order": "asc"}],
            )
            menus = [MenuOutSchema.model_validate(menu) for menu in menu_all]
        else:
            menu_ids = {menu.id for role in self.auth.user.roles or [] for menu in role.menus if menu.status == 0 and getattr(menu, "client", "pc") == "pc"}

            menus = (
                [
                    MenuOutSchema.model_validate(menu)
                    for menu in await MenuCRUD(self.auth).tree_list(
                        search={"id": ("in", list(menu_ids)), **_pc_only},
                        order_by=[{"order": "asc"}],
                    )
                ]
                if menu_ids
                else []
            )
        user_dict.menus = traversal_to_tree([menu.model_dump() for menu in menus])
        return user_dict

    async def update_current_info(self, data: CurrentUserUpdateSchema) -> UserOutSchema:
        if not self.auth.user or not self.auth.user.id:
            raise CustomException(msg="该数据不存在")
        user = await UserCRUD(self.auth).get(id=self.auth.user.id)
        if not user:
            raise CustomException(msg="该数据不存在")
        if user.is_superuser:
            raise CustomException(msg="超级管理员不能修改个人信息")
        if data.mobile:
            exist_mobile_user = await UserCRUD(self.auth).get(mobile=data.mobile)
            if exist_mobile_user and exist_mobile_user.id != self.auth.user.id:
                raise CustomException(msg="该数据已存在")
        if data.email:
            exist_email_user = await UserCRUD(self.auth).get(email=data.email)
            if exist_email_user and exist_email_user.id != self.auth.user.id:
                raise CustomException(msg="该数据已存在")
        user_update_data = UserUpdateSchema(**data.model_dump())
        new_user = await UserCRUD(self.auth).update(id=self.auth.user.id, data=user_update_data)
        return UserOutSchema.model_validate(new_user)

    async def set_available(self, data: BatchSetAvailable) -> None:
        for mid in data.ids:
            user = await UserCRUD(self.auth).get_or_404(id=mid)
            if user.is_superuser:
                raise CustomException(msg="超级管理员状态不能修改")
        await UserCRUD(self.auth).set(ids=data.ids, status=data.status)

    async def change_password(self, data: UserChangePasswordSchema) -> UserOutSchema:
        if not self.auth.user or not self.auth.user.id:
            raise CustomException(msg="该数据不存在")
        if not data.old_password or not data.new_password:
            raise CustomException(msg="密码不能为空")

        user = await UserCRUD(self.auth).get(id=self.auth.user.id)
        if not user:
            raise CustomException(msg="该数据不存在")
        if not PwdUtil.verify_password(plain_password=data.old_password, password_hash=user.password):
            raise CustomException(msg="原密码输入错误")

        new_password_hash = PwdUtil.hash_password(password=data.new_password)
        new_user = await UserCRUD(self.auth).change_password(id=user.id, password_hash=new_password_hash)
        return UserOutSchema.model_validate(new_user)

    async def reset_password(self, data: ResetPasswordSchema) -> UserOutSchema:
        if not data.password:
            raise CustomException(msg="密码不能为空")

        user = await UserCRUD(self.auth).get(id=data.id)
        if not user:
            raise CustomException(msg="该数据不存在")

        if user.is_superuser:
            raise CustomException(msg="超级管理员密码不能重置")

        new_password_hash = PwdUtil.hash_password(password=data.password)
        new_user = await UserCRUD(self.auth).change_password(id=data.id, password_hash=new_password_hash)
        return UserOutSchema.model_validate(new_user)

    async def register(self, data: UserRegisterSchema) -> UserOutSchema:
        username_ok = await UserCRUD(self.auth).get(username=data.username)
        if username_ok:
            raise CustomException(msg="该数据已存在")

        data.password = PwdUtil.hash_password(password=data.password)
        data.name = data.username
        create_dict = data.model_dump(exclude_unset=True, exclude={"role_ids"})

        if self.auth.user and self.auth.user.id:
            create_dict["created_id"] = self.auth.user.id

        result = await UserCRUD(self.auth).create(data=create_dict)
        if data.role_ids:
            await UserCRUD(self.auth).set_user_roles(user_ids=[result.id], role_ids=data.role_ids)
        return UserOutSchema.model_validate(result)

    async def forget_password(self, data: UserForgetPasswordSchema) -> UserOutSchema:
        user = await UserCRUD(self.auth).get(username=data.username)
        if not user:
            raise CustomException(msg="该数据不存在")
        if user.status == 1:
            raise CustomException(msg="用户已停用")

        if user.is_superuser:
            raise CustomException(msg="超级管理员密码不能重置")

        if data.mobile and user.mobile != data.mobile:
            raise CustomException(msg="手机号不匹配")

        new_password_hash = PwdUtil.hash_password(password=data.new_password)
        new_user = await UserCRUD(self.auth).forget_password(id=user.id, password_hash=new_password_hash)
        return UserOutSchema.model_validate(new_user)
