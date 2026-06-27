"""SmartQA sync schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QianniuSyncDbSchema(BaseModel):
    """Source database sync request."""

    build: bool = Field(True, description="Rebuild DIM/DWD after syncing")
    seed: bool = Field(True, description="Seed rules, menus and accounts")
    truncate_dwd: bool = Field(False, description="Clear DIM/DWD/QC before rebuilding")


class QianniuBatchSchema(BaseModel):
    """Sync batch response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: str
    source_system: str
    source_type: str
    chat_rows: int
    shop_rows: int
    conversation_count: int
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_time: datetime


class QianniuSyncResultSchema(BaseModel):
    """Sync result response."""

    batch_id: str
    chat_rows: int
    shop_rows: int
    conversation_count: int
    elapsed_seconds: float | None = None
    build_result: dict = Field(default_factory=dict)
    seed_result: dict = Field(default_factory=dict)


class QianniuSyncScheduleSchema(BaseModel):
    """SmartQA scheduler status."""

    scheduler_enabled: bool
    scheduler_running: bool
    timezone: str
    source_sync_times: str
    daily_qc_time: str
    daily_qc_sample_limit: int
    daily_qc_execute: bool
    jobs: list[dict] = Field(default_factory=list)
