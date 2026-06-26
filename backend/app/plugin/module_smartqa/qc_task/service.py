"""质检任务管理服务。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_smartqa.models.qc import QcTaskModel

from .executor import QcTaskExecutor
from .schema import QcTaskCreateSchema, QcTaskExecuteSchema


class QcTaskService:
    """质检任务管理服务。"""

    def __init__(self, auth: AuthSchema):
        self.auth = auth
        self.executor = QcTaskExecutor(auth)

    async def create_tasks(self, session: AsyncSession, data: QcTaskCreateSchema) -> list[QcTaskModel]:
        """批量创建质检任务。"""
        tasks = await self.executor.create_tasks(
            session,
            data.conversation_ids,
            data.rule_version,
            data.model_name,
        )
        await session.commit()
        return tasks

    async def execute_tasks(self, session: AsyncSession, data: QcTaskExecuteSchema) -> list[dict]:
        """批量执行质检任务。"""
        results = []
        for task_id in data.task_ids[: data.batch_size]:
            try:
                result = await self.executor.execute_task(session, task_id)
                results.append(result)
                await session.commit()
            except Exception as e:
                results.append({
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                })
                await session.rollback()

        return results

    async def get_task(self, session: AsyncSession, task_id: int) -> QcTaskModel:
        """获取任务详情。"""
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
        """获取任务列表。"""
        stmt = select(QcTaskModel).where(QcTaskModel.is_deleted == False)  # noqa: E712

        if conversation_id:
            stmt = stmt.where(QcTaskModel.conversation_id == conversation_id)
        if status:
            stmt = stmt.where(QcTaskModel.status == status)

        stmt = stmt.order_by(QcTaskModel.created_time.desc()).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())
