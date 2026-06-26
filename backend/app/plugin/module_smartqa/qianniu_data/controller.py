from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import ImportBatchQueryParam
from .service import QianniuDataService

QianniuDataRouter = APIRouter(route_class=OperationLogRoute, prefix="/qianniu", tags=["SmartQA", "千牛数据源"])
router = QianniuDataRouter  # Alias for router import


@QianniuDataRouter.get("/batches", summary="千牛同步批次列表", response_model=ResponseSchema[dict])
async def get_import_batch_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ImportBatchQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await QianniuDataService(auth).batch_page(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询千牛同步批次成功")


@QianniuDataRouter.get("/summary", summary="千牛数据源摘要", response_model=ResponseSchema[dict])
async def get_qianniu_summary_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await QianniuDataService(auth).latest_summary()
    return SuccessResponse(data=result, msg="查询千牛数据源摘要成功")

