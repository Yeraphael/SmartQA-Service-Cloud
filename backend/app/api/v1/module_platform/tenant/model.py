from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin


class TenantModel(ModelMixin):
    """
    单租户底座模型。

    SmartQA P0 为单业务产品形态。
    该表仅保留登录上下文和基础站点配置所需字段。
    """

    __tablename__: str = "platform_tenant"
    __table_args__: dict[str, str] = {"comment": "租户表"}
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="租户名称")
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="租户编码")
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, comment="联系人姓名")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None, comment="联系人电话")
    contact_email: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None, comment="联系人邮箱")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, comment="地址")
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, comment="域名")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="Logo URL")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, comment="开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, comment="结束时间")
    version: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None, comment="版本号")
    favicon: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="favicon地址")
    login_bg: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="登录背景地址")
    copyright: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, comment="版权信息")
    keep_record: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None, comment="备案号")
    help_doc: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="帮助文档地址")
    privacy: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="隐私政策地址")
    clause: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="服务条款地址")
    git_code: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="源码地址")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启动 1:停用)", index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")

    @validates("name")
    def validate_name(self, key: str, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("名称不能为空")
        return name

    @validates("code")
    def validate_code(self, key: str, code: str) -> str:
        if not code or not code.strip():
            raise ValueError("编码不能为空")
        if not code.isalnum():
            raise ValueError("编码只能包含字母和数字")
        return code
