from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import SmartQARoute

from .service import DashboardService

DashboardRouter = APIRouter(route_class=SmartQARoute, prefix="/dashboard", tags=["SmartQA", "看板"])
router = DashboardRouter  # Alias for router import


@DashboardRouter.get("/overview", summary="看板总览", response_model=ResponseSchema[dict])
async def get_dashboard_overview_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await DashboardService(auth).overview()
    return SuccessResponse(data=result, msg="查询看板总览成功")


@DashboardRouter.get("/staff-ranking", summary="客服表现排行", response_model=ResponseSchema[list[dict]])
async def get_staff_ranking_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
) -> JSONResponse:
    result = await DashboardService(auth).staff_ranking(limit=limit)
    return SuccessResponse(data=result, msg="查询客服排行成功")


@DashboardRouter.get("/issue-distribution", summary="问题类型分布", response_model=ResponseSchema[list[dict]])
async def get_issue_distribution_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await DashboardService(auth).issue_distribution()
    return SuccessResponse(data=result, msg="查询问题分布成功")


@DashboardRouter.get("/shop-distribution", summary="店铺会话分布", response_model=ResponseSchema[list[dict]])
async def get_shop_distribution_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await DashboardService(auth).shop_distribution()
    return SuccessResponse(data=result, msg="查询店铺分布成功")


@DashboardRouter.get("/staff-performance", summary="客服表现统计", response_model=ResponseSchema[list[dict]])
async def get_staff_performance_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
    staff_id: int | None = Query(None, ge=1, description="客服ID"),
    limit: int = Query(100, ge=1, le=200, description="返回数量"),
) -> JSONResponse:
    result = await DashboardService(auth).staff_performance(staff_id=staff_id, limit=limit)
    return SuccessResponse(data=result, msg="查询客服表现成功")


@DashboardRouter.get("/improvements", summary="改进建议汇总", response_model=ResponseSchema[dict])
async def get_improvements_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    staff_id: int | None = Query(None, ge=1, description="客服ID"),
) -> JSONResponse:
    result = await DashboardService(auth).improvements(limit=limit, staff_id=staff_id)
    return SuccessResponse(data=result, msg="查询改进建议成功")
