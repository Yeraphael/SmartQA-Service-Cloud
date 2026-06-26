from sqlalchemy import desc, func, select

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.common.pagination import paginate_query
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel
from app.plugin.module_smartqa.models.ods import OdsQnChatRecordModel, OdsQnShopRecordModel
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
        batch_rows = (
            await self.auth.db.execute(
                select(OdsImportBatchModel.status).where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
            )
        ).all()
        chat_rows = (
            await self.auth.db.execute(
                select(func.count()).select_from(OdsQnChatRecordModel).where(OdsQnChatRecordModel.is_deleted == False)  # noqa: E712
            )
        ).scalar_one()
        shop_rows = (
            await self.auth.db.execute(
                select(func.count()).select_from(OdsQnShopRecordModel).where(OdsQnShopRecordModel.is_deleted == False)  # noqa: E712
            )
        ).scalar_one()
        conversation_count = (
            await self.auth.db.execute(
                select(func.count()).select_from(DwdQnConversationModel).where(DwdQnConversationModel.is_deleted == False)  # noqa: E712
            )
        ).scalar_one()
        return {
            "latest_batch_id": latest.batch_id if latest else None,
            "latest_status": latest.status if latest else None,
            "latest_finished_at": latest.finished_at if latest else None,
            "batch_count": len(batch_rows),
            "success_batch_count": sum(1 for row in batch_rows if row.status == "success"),
            "chat_rows": chat_rows,
            "shop_rows": shop_rows,
            "conversation_count": conversation_count,
        }
