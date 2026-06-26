"""质检任务管理控制器。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.plugin.module_smartqa.common.access import ensure_smartqa_boss

from .schema import QcTaskCreateSchema, QcTaskExecuteSchema, QcTaskResultSchema, QcTaskSchema
from .service import QcTaskService

router = APIRouter(prefix="/qc/tasks", tags=["SmartQA - 质检任务"])


@router.post("", summary="批量创建质检任务", response_model=ResponseSchema[list[QcTaskSchema]])
async def create_tasks(
    data: QcTaskCreateSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """批量创建质检任务。"""
    await ensure_smartqa_boss(auth)
    service = QcTaskService(auth)
    tasks = await service.create_tasks(session, data)
    return SuccessResponse(data=[QcTaskSchema.model_validate(task) for task in tasks], msg="创建成功")


@router.post("/execute", summary="批量执行质检任务", response_model=ResponseSchema[list[QcTaskResultSchema]])
async def execute_tasks(
    data: QcTaskExecuteSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """批量执行质检任务。"""
    await ensure_smartqa_boss(auth)
    service = QcTaskService(auth)
    results = await service.execute_tasks(session, data)
    return SuccessResponse(data=[QcTaskResultSchema.model_validate(r) for r in results], msg="执行完成")


@router.get("/{task_id}", summary="获取任务详情", response_model=ResponseSchema[QcTaskSchema])
async def get_task(
    task_id: int,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    """获取任务详情。"""
    await ensure_smartqa_boss(auth)
    service = QcTaskService(auth)
    task = await service.get_task(session, task_id)
    return SuccessResponse(data=QcTaskSchema.model_validate(task), msg="查询成功")


@router.get("", summary="获取任务列表", response_model=ResponseSchema[list[QcTaskSchema]])
async def list_tasks(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    conversation_id: int | None = Query(None, description="会话ID"),
    status: str | None = Query(None, description="任务状态"),
    limit: int = Query(100, description="返回数量", ge=1, le=500),
):
    """获取任务列表。"""
    await ensure_smartqa_boss(auth)
    service = QcTaskService(auth)
    tasks = await service.list_tasks(session, conversation_id, status, limit)
    return SuccessResponse(data=[QcTaskSchema.model_validate(task) for task in tasks], msg="查询成功")
