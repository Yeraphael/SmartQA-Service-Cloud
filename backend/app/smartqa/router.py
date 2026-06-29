"""SmartQA system API router."""

from fastapi import APIRouter

from app.smartqa.conversation.controller import router as conversation_router
from app.smartqa.dashboard.controller import router as dashboard_router
from app.smartqa.health.controller import router as health_router
from app.smartqa.qc_result.controller import router as qc_result_router
from app.smartqa.qc_rule.controller import router as qc_rule_router
from app.smartqa.qc_task.controller import router as qc_task_router
from app.smartqa.qianniu_data.controller import router as qianniu_data_router
from app.smartqa.staff_user.controller import router as staff_user_router
from app.smartqa.sync.controller import router as sync_router

smartqa_router = APIRouter(prefix="/smartqa", tags=["SmartQA"])

smartqa_router.include_router(health_router)
smartqa_router.include_router(dashboard_router)
smartqa_router.include_router(sync_router)
smartqa_router.include_router(conversation_router)
smartqa_router.include_router(qianniu_data_router)
smartqa_router.include_router(qc_result_router)
smartqa_router.include_router(qc_rule_router)
smartqa_router.include_router(qc_task_router)
smartqa_router.include_router(staff_user_router)
