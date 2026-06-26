"""客服账号管理Schema。"""

from pydantic import BaseModel, Field


class StaffUserSeedSchema(BaseModel):
    """批量初始化客服账号。"""

    force: bool = Field(False, description="是否强制重新创建已绑定的账号")


class StaffUserBindSchema(BaseModel):
    """绑定客服到系统用户。"""

    staff_id: int = Field(..., description="客服ID")
    user_id: int = Field(..., description="系统用户ID")


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
