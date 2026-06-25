from pydantic import BaseModel, Field


class SmartQAHealthSchema(BaseModel):
    """SmartQA startup status."""

    service: str = Field(default="smartqa", description="服务标识")
    status: str = Field(default="ok", description="状态")
    source_db_name: str = Field(..., description="千牛源库名称")
    target_db_name: str = Field(..., description="业务库名称")
    boss_username: str = Field(..., description="老板初始账号")
    ali_model_name: str = Field(..., description="阿里模型名称")
    qc_task_concurrency: int = Field(..., description="质检任务并发数")
    sync_overlap_minutes: int = Field(..., description="同步重叠窗口分钟")
    shop_record_rolling_days: int = Field(..., description="业务记录滚动刷新天数")
