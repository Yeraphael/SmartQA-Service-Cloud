from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import redis_getter

from .schema import DictDataOutSchema
from .service import DictDataService

PublicDictRouter = APIRouter(prefix="/dict", tags=["系统初始化"])


@PublicDictRouter.get(
    "/data/info/{dict_type}",
    summary="根据字典类型获取数据",
    response_model=ResponseSchema[list[DictDataOutSchema]],
)
async def get_init_dict_data_controller(
    dict_type: str,
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    dict_data_query_result = await DictDataService.get_init_cache(
        redis=redis,
        dict_type=dict_type,
        tenant_id=1,
    )
    return SuccessResponse(data=dict_data_query_result, msg="获取初始化字典数据成功")
