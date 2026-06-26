from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import QcResultDetailSchema, QcResultQueryParam
from .service import QcResultService

QcResultRouter = APIRouter(route_class=OperationLogRoute, prefix="/qc/results", tags=["SmartQA", "质检结果"])
router = QcResultRouter  # Alias for router import


@QcResultRouter.get("/list", summary="质检结果列表", response_model=ResponseSchema[dict])
async def get_qc_result_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[QcResultQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await QcResultService(auth).page(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询质检结果成功")


@QcResultRouter.get("/detail/{id}", summary="质检结果详情", response_model=ResponseSchema[QcResultDetailSchema])
async def get_qc_result_detail_controller(
    id: Annotated[int, Path(description="质检结果主键ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await QcResultService(auth).detail(id=id)
    return SuccessResponse(data=result, msg="查询质检结果详情成功")

