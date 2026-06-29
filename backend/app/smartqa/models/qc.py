from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class QcRuleModel(ModelMixin, TenantMixin, UserMixin):
    """质检规则表。"""

    __tablename__: str = "qc_rule"
    __table_args__ = (
        UniqueConstraint("rule_code", name="uq_qc_rule_code"),
        {"comment": "质检规则表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="规则编码")
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="规则分类")
    judgment_standard: Mapped[str] = mapped_column(Text, nullable=False, comment="判断标准")
    deduction_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="扣分")
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False, index=True, comment="严重程度")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class QcPromptTemplateModel(ModelMixin, TenantMixin, UserMixin):
    """Prompt 模板表。"""

    __tablename__: str = "qc_prompt_template"
    __table_args__ = (
        UniqueConstraint("prompt_version", name="uq_qc_prompt_template_version"),
        {"comment": "Prompt 模板表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, comment="Prompt版本")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    template_content: Mapped[str] = mapped_column(Text, nullable=False, comment="模板内容")
    output_schema_version: Mapped[str] = mapped_column(String(64), nullable=False, comment="输出结构版本")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")


class QcRuleVersionModel(ModelMixin, TenantMixin, UserMixin):
    """质检规则版本快照表。"""

    __tablename__: str = "qc_rule_version"
    __table_args__ = (
        UniqueConstraint("rule_version", name="uq_qc_rule_version"),
        {"comment": "质检规则版本快照表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, comment="规则版本")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Prompt版本")
    rule_codes: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="规则编码列表")
    rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="规则快照")
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True, comment="状态")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")


class QcTaskModel(ModelMixin, TenantMixin, UserMixin):
    """AI 质检任务表。"""

    __tablename__: str = "qc_task"
    __table_args__ = (
        UniqueConstraint("conversation_id", "conversation_data_hash", "rule_version", "prompt_version", name="uq_qc_task_version"),
        {"comment": "AI 质检任务表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="任务ID")
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("dwd_qn_conversation.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="会话ID")
    conversation_data_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话数据哈希")
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="规则版本")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Prompt版本")
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="模型名称")
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True, comment="状态")
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="模型结构化响应")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")


class QcResultModel(ModelMixin, TenantMixin, UserMixin):
    """质检结果主表。"""

    __tablename__: str = "qc_result"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_qc_result_task"),
        {"comment": "质检结果主表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    result_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="结果ID")
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("qc_task.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="任务ID")
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("dwd_qn_conversation.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="会话ID")
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="总分")
    result_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="结果等级")
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="风险等级")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    dimension_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="维度分")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True, comment="置信度")


class QcIssueModel(ModelMixin, TenantMixin, UserMixin):
    """质检扣分/问题明细表。"""

    __tablename__: str = "qc_issue"
    __table_args__: dict[str, str] = {"comment": "质检扣分/问题明细表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    issue_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="问题ID")
    result_id: Mapped[int] = mapped_column(Integer, ForeignKey("qc_result.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="结果ID")
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="规则编码")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="严重程度")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="问题标题")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="判断原因")
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理建议")
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推荐话术")
    deduction_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="扣分")


class QcIssueEvidenceModel(ModelMixin, TenantMixin, UserMixin):
    """问题证据消息表。"""

    __tablename__: str = "qc_issue_evidence"
    __table_args__ = (
        UniqueConstraint("issue_id", "message_id", name="uq_qc_issue_evidence_issue_message"),
        {"comment": "问题证据消息表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="证据ID")
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("qc_issue.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="问题ID")
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("dwd_qn_message.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="消息ID")
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="证据文本")


class ModelCallLogModel(ModelMixin, TenantMixin, UserMixin):
    """模型调用日志表。"""

    __tablename__: str = "model_call_log"
    __table_args__ = (
        UniqueConstraint("call_id", name="uq_model_call_log_call_id"),
        {"comment": "模型调用日志表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    call_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="调用ID")
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("qc_task.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="任务ID")
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="模型名称")
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="请求体")
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="响应体")
    raw_response_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始响应文本")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="输入Token")
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="输出Token")
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否成功")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
