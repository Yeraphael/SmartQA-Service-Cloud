"""SmartQA source database sync controllers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.ap_scheduler import SchedulerUtil
from app.core.dependencies import AuthPermission, db_getter
from app.smartqa.common.access import ensure_smartqa_boss

from .db_sync_service import SourceDbSyncService
from .schema import QianniuBatchSchema, QianniuSyncDbSchema, QianniuSyncResultSchema, QianniuSyncScheduleSchema
from .service import QianniuSyncService

router = APIRouter(prefix="/sync", tags=["SmartQA - Qianniu Sync"])


@router.post("/source-db", summary="Sync real Qianniu data from source DB", response_model=ResponseSchema[QianniuSyncResultSchema])
async def sync_from_source_db(
    data: QianniuSyncDbSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """Sync from the aizhijian source database and optionally rebuild DIM/DWD."""
    await ensure_smartqa_boss(auth)
    service = SourceDbSyncService(auth=auth)
    result = await service.full_sync(session, build=data.build, seed=data.seed, truncate_dwd=data.truncate_dwd)
    return SuccessResponse(data=QianniuSyncResultSchema.model_validate(result), msg="Source database sync succeeded")


@router.get("/schedule", summary="Get SmartQA sync schedule", response_model=ResponseSchema[QianniuSyncScheduleSchema])
async def get_sync_schedule(auth: AuthSchema = Depends(AuthPermission())):
    """Return configured source sync and daily QC schedule."""
    await ensure_smartqa_boss(auth)
    data = QianniuSyncScheduleSchema(
        scheduler_enabled=settings.SCHEDULER_ENABLE,
        scheduler_running=SchedulerUtil.is_running(),
        timezone=settings.SMARTQA_SCHEDULER_TIMEZONE,
        source_sync_times=settings.SMARTQA_SOURCE_SYNC_TIMES,
        daily_qc_time=settings.SMARTQA_DAILY_QC_TIME,
        daily_qc_sample_limit=settings.SMARTQA_DAILY_QC_SAMPLE_LIMIT,
        daily_qc_execute=settings.SMARTQA_DAILY_QC_EXECUTE,
        jobs=SchedulerUtil.get_jobs(),
    )
    return SuccessResponse(data=data, msg="Query succeeded")


@router.get("/batches", summary="List sync batches", response_model=ResponseSchema[list[QianniuBatchSchema]])
async def list_batches(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    limit: int = Query(50, description="Number of batches", ge=1, le=200),
):
    """Return recent source database sync batches."""
    await ensure_smartqa_boss(auth)
    service = QianniuSyncService(auth)
    batches = await service.list_batches(session, limit)
    return SuccessResponse(data=[QianniuBatchSchema.model_validate(b) for b in batches], msg="Query succeeded")


@router.get("/batches/{batch_id}", summary="Get sync batch detail", response_model=ResponseSchema[QianniuBatchSchema])
async def get_batch(
    batch_id: str,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """Return one sync batch detail."""
    await ensure_smartqa_boss(auth)
    service = QianniuSyncService(auth)
    batch = await service.get_batch(session, batch_id)
    return SuccessResponse(data=QianniuBatchSchema.model_validate(batch), msg="Query succeeded")
