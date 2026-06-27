"""SmartQA QC task service."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_smartqa.models.qc import QcTaskModel
from app.plugin.module_smartqa.pipeline import SmartQAPipeline

from .executor import QcTaskExecutor
from .schema import QcDailySampleSchema, QcTaskCreateSchema, QcTaskExecuteSchema


class QcTaskService:
    """Quality-check task management."""

    def __init__(self, auth: AuthSchema):
        self.auth = auth
        self.executor = QcTaskExecutor(auth)

    async def create_tasks(self, session: AsyncSession, data: QcTaskCreateSchema) -> list[QcTaskModel]:
        """Create QC tasks for selected conversations."""
        tasks = await self.executor.create_tasks(
            session,
            data.conversation_ids,
            data.rule_version,
            data.model_name,
        )
        await session.commit()
        return tasks

    async def execute_tasks(self, session: AsyncSession, data: QcTaskExecuteSchema) -> list[dict]:
        """Execute selected QC tasks."""
        results = []
        for task_id in data.task_ids[: data.batch_size]:
            try:
                result = await self.executor.execute_task(session, task_id)
                results.append(result)
                await session.commit()
            except Exception as e:
                results.append(
                    {
                        "task_id": task_id,
                        "status": "failed",
                        "error": str(e),
                    }
                )
                await session.rollback()

        return results

    async def run_daily_sample(self, data: QcDailySampleSchema) -> dict:
        """Create and optionally execute the daily QC sample."""
        pipeline = SmartQAPipeline(
            tenant_id=self.auth.tenant_id,
            created_id=self.auth.user_id,
        )
        return await asyncio.to_thread(
            pipeline.run_daily_qc_sample,
            limit=data.limit,
            execute=data.execute,
            model_name=data.model_name,
            rule_version=data.rule_version,
        )

    async def get_task(self, session: AsyncSession, task_id: int) -> QcTaskModel:
        """Get one task."""
        stmt = select(QcTaskModel).where(
            QcTaskModel.id == task_id,
            QcTaskModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise CustomException("任务不存在")
        return task

    async def list_tasks(
        self,
        session: AsyncSession,
        conversation_id: int | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[QcTaskModel]:
        """List recent tasks."""
        stmt = select(QcTaskModel).where(QcTaskModel.is_deleted == False)  # noqa: E712

        if conversation_id:
            stmt = stmt.where(QcTaskModel.conversation_id == conversation_id)
        if status:
            stmt = stmt.where(QcTaskModel.status == status)

        stmt = stmt.order_by(QcTaskModel.created_time.desc()).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())
