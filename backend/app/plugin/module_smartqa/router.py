"""SmartQA模块统一路由。"""

from fastapi import APIRouter

from app.plugin.module_smartqa.conversation.controller import router as conversation_router
from app.plugin.module_smartqa.dashboard.controller import router as dashboard_router
from app.plugin.module_smartqa.health.controller import router as health_router
from app.plugin.module_smartqa.qc_result.controller import router as qc_result_router
from app.plugin.module_smartqa.qc_rule.controller import router as qc_rule_router
from app.plugin.module_smartqa.qc_task.controller import router as qc_task_router
from app.plugin.module_smartqa.qianniu_data.controller import router as qianniu_data_router
from app.plugin.module_smartqa.staff_user.controller import router as staff_user_router
from app.plugin.module_smartqa.sync.controller import router as sync_router

smartqa_router = APIRouter(prefix="/api/v1/smartqa", tags=["SmartQA"])

smartqa_router.include_router(health_router)
smartqa_router.include_router(dashboard_router)
smartqa_router.include_router(sync_router)
smartqa_router.include_router(conversation_router)
smartqa_router.include_router(qianniu_data_router)
smartqa_router.include_router(qc_result_router)
smartqa_router.include_router(qc_rule_router)
smartqa_router.include_router(qc_task_router)
smartqa_router.include_router(staff_user_router)
