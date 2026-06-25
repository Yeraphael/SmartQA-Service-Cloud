from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.router_class import OperationLogRoute

from .schema import SmartQAHealthSchema

SmartQAHealthRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/health",
    tags=["SmartQA", "健康检查"],
)


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
    )
    return SuccessResponse(data=data, msg="SmartQA 服务正常")

