from sqlalchemy import desc, select

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.common.pagination import paginate_query
from app.plugin.module_smartqa.models.ods import OdsImportBatchModel

from .schema import ImportBatchQueryParam


class QianniuDataService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def batch_page(self, page_no: int, page_size: int, search: ImportBatchQueryParam) -> dict:
        stmt = (
            select(
                OdsImportBatchModel.id,
                OdsImportBatchModel.batch_id,
                OdsImportBatchModel.source_system,
                OdsImportBatchModel.source_type,
                OdsImportBatchModel.checkpoint,
                OdsImportBatchModel.chat_rows,
                OdsImportBatchModel.shop_rows,
                OdsImportBatchModel.conversation_count,
                OdsImportBatchModel.status,
                OdsImportBatchModel.error_message,
                OdsImportBatchModel.started_at,
                OdsImportBatchModel.finished_at,
                OdsImportBatchModel.created_time,
            )
            .where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
            .order_by(desc(OdsImportBatchModel.created_time), desc(OdsImportBatchModel.id))
        )
        if search.status:
            stmt = stmt.where(OdsImportBatchModel.status == search.status)
        if search.source_type:
            stmt = stmt.where(OdsImportBatchModel.source_type == search.source_type)
        return await paginate_query(self.auth.db, stmt, page_no, page_size)

    async def latest_summary(self) -> dict:
        latest_stmt = (
            select(OdsImportBatchModel)
            .where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
            .order_by(desc(OdsImportBatchModel.created_time), desc(OdsImportBatchModel.id))
            .limit(1)
        )
        latest = (await self.auth.db.execute(latest_stmt)).scalars().first()
        total_stmt = select(
            OdsImportBatchModel.status,
            OdsImportBatchModel.chat_rows,
            OdsImportBatchModel.shop_rows,
            OdsImportBatchModel.conversation_count,
        ).where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
        rows = (await self.auth.db.execute(total_stmt)).all()
        return {
            "latest_batch_id": latest.batch_id if latest else None,
            "latest_status": latest.status if latest else None,
            "latest_finished_at": latest.finished_at if latest else None,
            "batch_count": len(rows),
            "success_batch_count": sum(1 for row in rows if row.status == "success"),
            "chat_rows": sum(row.chat_rows or 0 for row in rows),
            "shop_rows": sum(row.shop_rows or 0 for row in rows),
            "conversation_count": sum(row.conversation_count or 0 for row in rows),
        }

