"""客服账号管理Schema。"""

from pydantic import BaseModel, Field


class StaffUserSeedSchema(BaseModel):
    """批量初始化客服账号。"""

    force: bool = Field(False, description="是否强制重新创建已绑定的账号")


class StaffUserBindSchema(BaseModel):
    """绑定客服到系统用户。"""

    staff_id: int = Field(..., description="客服ID")
    user_id: int = Field(..., description="系统用户ID")


class StaffUserCreateSchema(BaseModel):
    """为单个客服创建或补绑定系统账号。"""

    password: str = Field("SmartQA@123456", min_length=8, max_length=128, description="初始密码")


class StaffUserResetPasswordSchema(BaseModel):
    """重置客服系统账号密码。"""

    password: str = Field("SmartQA@123456", min_length=8, max_length=128, description="新密码")


class StaffUserStatusSchema(BaseModel):
    """启停客服系统账号。"""

    status: int = Field(0, ge=0, le=1, description="账号状态，0启用，1停用")


class StaffUserListSchema(BaseModel):
    """客服账号列表响应。"""

    staff_id: int
    staff_key: str
    staff_name: str
    primary_account: str
    source_system: str
    status: str
    sys_user_id: int | None
    username: str | None
    nickname: str | None
    user_status: int | None
