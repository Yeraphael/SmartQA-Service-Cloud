from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TenantMixin
from app.smartqa.models.base import SmartQABulkModelMixin


class OdsImportBatchModel(SmartQABulkModelMixin, TenantMixin):
    """千牛导入/同步批次。"""

    __tablename__: str = "ods_import_batch"
    __table_args__ = (
        UniqueConstraint("batch_id", name="uq_ods_import_batch_batch_id"),
        {"comment": "SmartQA 数据导入/同步批次"},
    )
    __loader_options__: list[str] = ["tenant_by"]

    batch_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="批次ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    source_type: Mapped[str] = mapped_column(String(16), default="db", nullable=False, comment="来源类型(db/excel/api)")
    checkpoint: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="同步水位")
    chat_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="聊天行数")
    shop_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="业务行数")
    conversation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="会话数")
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True, comment="状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")


class OdsQnChatRecordModel(SmartQABulkModelMixin, TenantMixin):
    """千牛聊天明细原始表。"""

    __tablename__: str = "ods_qn_chat_record"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_ods_qn_chat_source_id"),
        Index("ix_ods_qn_chat_fingerprint", "source_system", "message_fingerprint"),
        {"comment": "千牛聊天明细原始表"},
    )
    __loader_options__: list[str] = ["tenant_by"]

    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="批次ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="源表ID")
    relation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="关系ID")
    business_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="业务ID")
    chat_target: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="说话方账号")
    chat_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="聊天内容")
    chat_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="聊天时间")
    source_create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="源表创建时间")
    message_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, comment="消息兜底指纹")
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="原始行哈希")
    first_seen_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="首次出现批次")
    last_seen_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最后出现批次")


class OdsQnShopRecordModel(SmartQABulkModelMixin, TenantMixin):
    """千牛咨询业务原始表。"""

    __tablename__: str = "ods_qn_shop_record"
    __table_args__ = (
        UniqueConstraint("source_system", "relation_id", "business_id", name="uq_ods_qn_shop_conversation"),
        {"comment": "千牛咨询业务原始表"},
    )
    __loader_options__: list[str] = ["tenant_by"]

    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="批次ID")
    source_system: Mapped[str] = mapped_column(String(32), default="qianniu", nullable=False, index=True, comment="来源系统")
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="源表ID")
    relation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="关系ID")
    business_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="业务ID")
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="店铺名称")
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True, comment="商品名称")
    product_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="商品ID")
    buyer_wangwang: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="买家旺旺脱敏值")
    seller_wangwang: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="客服旺旺")
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="咨询状态")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="结束时间")
    chat_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="业务表聊天摘要")
    source_create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="源表创建时间")
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="原始行哈希")
    first_seen_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="首次出现批次")
    last_seen_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最后出现批次")
