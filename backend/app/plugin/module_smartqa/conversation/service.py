from sqlalchemy import asc, desc, or_, select

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.common.access import build_staff_scope_condition, ensure_conversation_access
from app.plugin.module_smartqa.common.pagination import paginate_query
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel, DwdQnMessageModel
from app.plugin.module_smartqa.models.dimension import DimCustomerModel, DimProductModel, DimShopModel, DimStaffModel

from .schema import ConversationDetailSchema, ConversationQueryParam


class ConversationService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def page(self, page_no: int, page_size: int, search: ConversationQueryParam) -> dict:
        stmt = (
            select(
                DwdQnConversationModel.id,
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.relation_id,
                DwdQnConversationModel.business_id,
                DwdQnConversationModel.qn_status,
                DwdQnConversationModel.qc_status,
                DwdQnConversationModel.start_time,
                DwdQnConversationModel.end_time,
                DwdQnConversationModel.message_count,
                DwdQnConversationModel.first_response_seconds,
                DwdQnConversationModel.avg_response_seconds,
                DimShopModel.shop_name,
                DimProductModel.product_id,
                DimProductModel.product_name,
                DimStaffModel.staff_name,
                DimStaffModel.primary_account.label("staff_account"),
                DimCustomerModel.primary_taobao_account.label("customer_account"),
                DimCustomerModel.buyer_wangwang_masked,
            )
            .select_from(DwdQnConversationModel)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .where(DwdQnConversationModel.is_deleted == False)  # noqa: E712
        )

        scope_condition = await build_staff_scope_condition(self.auth)
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        if search.shop_id:
            stmt = stmt.where(DwdQnConversationModel.shop_id == search.shop_id)
        if search.staff_id:
            stmt = stmt.where(DwdQnConversationModel.staff_id == search.staff_id)
        if search.customer_id:
            stmt = stmt.where(DwdQnConversationModel.customer_id == search.customer_id)
        if search.qn_status:
            stmt = stmt.where(DwdQnConversationModel.qn_status == search.qn_status)
        if search.qc_status:
            stmt = stmt.where(DwdQnConversationModel.qc_status == search.qc_status)
        if search.start_time:
            stmt = stmt.where(DwdQnConversationModel.start_time >= search.start_time)
        if search.end_time:
            stmt = stmt.where(DwdQnConversationModel.start_time <= search.end_time)
        if search.keyword:
            keyword = f"%{search.keyword}%"
            stmt = stmt.where(
                or_(
                    DimProductModel.product_name.like(keyword),
                    DimStaffModel.staff_name.like(keyword),
                    DimStaffModel.primary_account.like(keyword),
                    DimCustomerModel.primary_taobao_account.like(keyword),
                    DimCustomerModel.buyer_wangwang_masked.like(keyword),
                )
            )

        stmt = stmt.order_by(desc(DwdQnConversationModel.start_time), desc(DwdQnConversationModel.id))
        return await paginate_query(self.auth.db, stmt, page_no, page_size)

    async def detail(self, id: int) -> ConversationDetailSchema:
        conversation_result = await self.auth.db.execute(
            select(DwdQnConversationModel).where(
                DwdQnConversationModel.id == id,
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
        )
        conversation = await ensure_conversation_access(self.auth, self.auth.db, conversation_result.scalars().first())

        summary_stmt = (
            select(
                DwdQnConversationModel.id,
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.relation_id,
                DwdQnConversationModel.business_id,
                DwdQnConversationModel.qn_status,
                DwdQnConversationModel.qc_status,
                DwdQnConversationModel.start_time,
                DwdQnConversationModel.end_time,
                DwdQnConversationModel.message_count,
                DimShopModel.shop_name,
                DimProductModel.product_id,
                DimProductModel.product_name,
                DimStaffModel.staff_name,
                DimStaffModel.primary_account.label("staff_account"),
                DimCustomerModel.primary_taobao_account.label("customer_account"),
                DimCustomerModel.buyer_wangwang_masked,
            )
            .select_from(DwdQnConversationModel)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .where(DwdQnConversationModel.id == conversation.id)
        )
        summary = (await self.auth.db.execute(summary_stmt)).mappings().first()

        message_stmt = (
            select(
                DwdQnMessageModel.id,
                DwdQnMessageModel.message_id,
                DwdQnMessageModel.source_message_id,
                DwdQnMessageModel.speaker_account,
                DwdQnMessageModel.speaker_type,
                DwdQnMessageModel.content_text,
                DwdQnMessageModel.message_time,
            )
            .where(
                DwdQnMessageModel.conversation_id == conversation.id,
                DwdQnMessageModel.is_deleted == False,  # noqa: E712
            )
            .order_by(asc(DwdQnMessageModel.message_time), asc(DwdQnMessageModel.id))
        )
        messages = (await self.auth.db.execute(message_stmt)).mappings().all()
        return ConversationDetailSchema(
            conversation=dict(summary or {}),
            messages=[dict(row) for row in messages],
        )

