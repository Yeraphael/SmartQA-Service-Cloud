"""质检任务管理Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QcTaskCreateSchema(BaseModel):
    """创建质检任务。"""

    conversation_ids: list[int] = Field(..., description="会话ID列表")
    rule_version: str = Field(..., description="规则版本")
    model_name: str = Field("qwen3.7-plus", description="模型名称")


class QcTaskExecuteSchema(BaseModel):
    """执行质检任务。"""

    task_ids: list[int] = Field(..., description="任务ID列表")
    batch_size: int = Field(10, description="批量执行大小", ge=1, le=100)


class QcDailySampleSchema(BaseModel):
    """每日质检抽样。"""

    limit: int = Field(100, description="抽检会话数", ge=1, le=1000)
    execute: bool = Field(False, description="是否立即调用模型执行")
    rule_version: str = Field("smartqa-p0-20260625", description="规则版本")
    model_name: str | None = Field(None, description="模型名称")


class QcTaskSchema(BaseModel):
    """质检任务响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: str
    conversation_id: int
    rule_version: str
    prompt_version: str
    model_name: str
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_time: datetime


class QcTaskResultSchema(BaseModel):
    """任务执行结果。"""

    task_id: str | int
    status: str
    result: dict | None = None
    error: str | None = None
