from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class DimShopModel(ModelMixin, TenantMixin, UserMixin):
    """店铺维表。"""

    __tablename__: str = "dim_shop"
    __table_args__ = (
        UniqueConstraint("source_system", "shop_name", name="uq_dim_shop_source_name"),
        {"comment": "店铺维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="店铺业务键")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="店铺名称")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class DimProductModel(ModelMixin, TenantMixin, UserMixin):
    """商品维表。"""

    __tablename__: str = "dim_product"
    __table_args__ = (
        UniqueConstraint("source_system", "shop_id", "product_id", name="uq_dim_product_source_shop_product"),
        {"comment": "商品维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    product_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="商品业务键")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_shop.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="店铺ID")
    product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="平台商品ID")
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True, comment="商品名称")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class DimStaffModel(ModelMixin, TenantMixin, UserMixin):
    """客服维表。"""

    __tablename__: str = "dim_staff"
    __table_args__ = (
        UniqueConstraint("source_system", "primary_account", name="uq_dim_staff_source_account"),
        {"comment": "客服维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    staff_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="客服业务键")
    staff_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="客服名称")
    primary_account: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="主账号")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    sys_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="绑定系统用户ID")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class DimStaffAccountModel(ModelMixin, TenantMixin, UserMixin):
    """客服渠道账号维表。"""

    __tablename__: str = "dim_staff_account"
    __table_args__ = (
        UniqueConstraint("source_system", "shop_id", "account_name", name="uq_dim_staff_account_source_shop_account"),
        {"comment": "客服渠道账号维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    staff_account_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="客服账号业务键")
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_staff.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客服ID")
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_shop.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="店铺ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    channel: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="渠道")
    account_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="平台账号")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class DimCustomerModel(ModelMixin, TenantMixin, UserMixin):
    """客户维表。"""

    __tablename__: str = "dim_customer"
    __table_args__ = (
        UniqueConstraint("first_source", "primary_taobao_account", name="uq_dim_customer_source_taobao"),
        {"comment": "客户维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    customer_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="客户业务键")
    primary_taobao_account: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="真实淘宝/旺旺账号")
    buyer_wangwang_masked: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="买家旺旺脱敏展示")
    first_source: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="首次来源")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="首次出现时间")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后出现时间")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class DimCustomerIdentityModel(ModelMixin, TenantMixin, UserMixin):
    """客户身份维表。"""

    __tablename__: str = "dim_customer_identity"
    __table_args__ = (
        UniqueConstraint("identity_type", "identity_value", name="uq_dim_customer_identity_type_value"),
        {"comment": "客户身份维表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_customer.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户ID")
    identity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="身份类型")
    identity_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="身份值")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    confidence: Mapped[str] = mapped_column(String(16), default="high", nullable=False, comment="置信度")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")
