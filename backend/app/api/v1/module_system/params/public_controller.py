from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import redis_getter

from .schema import ParamsOutSchema
from .service import ParamsService

PublicParamsRouter = APIRouter(prefix="/param", tags=["系统初始化"])


@PublicParamsRouter.get(
    "/info",
    summary="获取初始化缓存参数",
    response_model=ResponseSchema[list[ParamsOutSchema]],
)
async def get_init_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    result_dict = await ParamsService.get_init_cache(redis=redis, tenant_id=1)
    return SuccessResponse(data=result_dict, msg="获取初始化缓存参数成功")
