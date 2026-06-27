from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.router_class import SmartQARoute

from .schema import SmartQAHealthSchema

SmartQAHealthRouter = APIRouter(
    route_class=SmartQARoute,
    prefix="/health",
    tags=["SmartQA", "健康检查"],
)
router = SmartQAHealthRouter  # Alias for router import


@SmartQAHealthRouter.get(
    "/status",
    summary="SmartQA 健康检查",
    response_model=ResponseSchema[SmartQAHealthSchema],
)
async def get_smartqa_health_controller() -> JSONResponse:
    data = SmartQAHealthSchema(
        source_db_name=settings.SMARTQA_SOURCE_DB_NAME,
        target_db_name=settings.SMARTQA_TARGET_DB_NAME,
        boss_username=settings.SMARTQA_BOSS_USERNAME,
        ali_model_name=settings.SMARTQA_ALI_MODEL_NAME,
        qc_task_concurrency=settings.SMARTQA_QC_TASK_CONCURRENCY,
        sync_overlap_minutes=settings.SMARTQA_SYNC_OVERLAP_MINUTES,
        shop_record_rolling_days=settings.SMARTQA_SHOP_RECORD_ROLLING_DAYS,
        scheduler_enabled=settings.SCHEDULER_ENABLE,
        source_sync_times=settings.SMARTQA_SOURCE_SYNC_TIMES,
        daily_qc_time=settings.SMARTQA_DAILY_QC_TIME,
        daily_qc_sample_limit=settings.SMARTQA_DAILY_QC_SAMPLE_LIMIT,
    )
    return SuccessResponse(data=data, msg="SmartQA 服务正常")
