from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import JWTOutSchema
from app.core.validator import DateTimeStr


class CaptchaOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enable: bool = Field(default=True, description="是否启用验证码")
    key: str = Field(..., min_length=1, description="验证码唯一标识")
    img_base: str = Field(..., min_length=1, description="Base64 编码验证码图片")


class LoginOutSchema(JWTOutSchema):
    user_info: dict = Field(default_factory=dict, description="用户信息")


class OnlineOutSchema(BaseModel):
    name: str = Field(..., description="用户名称")
    session_id: str = Field(..., description="会话编号")
    user_id: int = Field(..., description="用户 ID")
    tenant_id: int = Field(..., description="内部站点 ID")
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    user_name: str = Field(..., description="用户名")
    ipaddr: str | None = Field(default=None, description="登录 IP")
    login_location: str | None = Field(default=None, description="登录归属地")
    os: str | None = Field(default=None, description="操作系统")
    browser: str | None = Field(default=None, description="浏览器")
    login_time: DateTimeStr | None = Field(default=None, description="登录时间")
    login_type: str | None = Field(default=None, description="登录类型")
