"""SmartQA sync batch query service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.smartqa.models.ods import OdsImportBatchModel


class QianniuSyncService:
    """Read-only helpers for SmartQA source-db sync batches."""

    def __init__(self, auth: AuthSchema | None = None):
        self.auth = auth

    async def list_batches(self, session: AsyncSession, limit: int = 50) -> list[OdsImportBatchModel]:
        """Return recent source-db sync batches."""
        stmt = (
            select(OdsImportBatchModel)
            .where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
            .order_by(OdsImportBatchModel.created_time.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_batch(self, session: AsyncSession, batch_id: str) -> OdsImportBatchModel:
        """Return one sync batch by id."""
        stmt = select(OdsImportBatchModel).where(
            OdsImportBatchModel.batch_id == batch_id,
            OdsImportBatchModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        batch = result.scalar_one_or_none()
        if not batch:
            raise CustomException("Sync batch not found")
        return batch
