from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class DwdQnConversationModel(ModelMixin, TenantMixin, UserMixin):
    """千牛会话主表。"""

    __tablename__: str = "dwd_qn_conversation"
    __table_args__ = (
        UniqueConstraint("source_system", "relation_id", "business_id", name="uq_dwd_qn_conversation_source_business"),
        {"comment": "千牛会话主表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    conversation_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, comment="会话业务键")
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="会话ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    relation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="关系ID")
    business_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="业务ID")
    shop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dim_shop.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="店铺ID")
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dim_product.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="商品维表ID")
    staff_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dim_staff.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="客服ID")
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dim_customer.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="客户ID")
    qn_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="千牛咨询状态")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="会话开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="会话结束时间")
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="消息数")
    customer_message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="客户消息数")
    staff_message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="客服消息数")
    first_response_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="首响秒数")
    avg_response_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="平均响应秒数")
    qc_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True, comment="质检状态")
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话数据版本哈希")


class DwdQnMessageModel(ModelMixin, TenantMixin, UserMixin):
    """千牛消息明细表。"""

    __tablename__: str = "dwd_qn_message"
    __table_args__ = (
        UniqueConstraint("source_system", "source_message_id", name="uq_dwd_qn_message_source_id"),
        UniqueConstraint("source_system", "message_fingerprint", name="uq_dwd_qn_message_fingerprint"),
        {"comment": "千牛消息明细表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    message_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="消息ID")
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("dwd_qn_conversation.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="会话主键ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    source_message_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="源消息ID")
    message_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, comment="兜底消息指纹")
    speaker_account: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="说话方账号")
    speaker_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="说话方类型")
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文本内容")
    message_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="消息时间")
    message_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="消息内容哈希")


class DwdCustomerStaffRelationModel(ModelMixin, TenantMixin, UserMixin):
    """客户客服服务关系表。"""

    __tablename__: str = "dwd_customer_staff_relation"
    __table_args__ = (
        UniqueConstraint("customer_id", "staff_id", "shop_id", name="uq_dwd_customer_staff_shop"),
        {"comment": "客户客服服务关系表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    relation_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="关系业务键")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_customer.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户ID")
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_staff.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客服ID")
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_shop.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="店铺ID")
    first_conversation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="首次会话时间")
    last_conversation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近会话时间")
    conversation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="会话数")

