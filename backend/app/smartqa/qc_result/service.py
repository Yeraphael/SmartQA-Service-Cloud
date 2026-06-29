from sqlalchemy import desc, or_, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.smartqa.common.access import build_staff_scope_condition
from app.smartqa.common.pagination import paginate_query
from app.smartqa.models.conversation import DwdQnConversationModel, DwdQnMessageModel
from app.smartqa.models.dimension import DimCustomerModel, DimProductModel, DimShopModel, DimStaffModel
from app.smartqa.models.qc import QcIssueEvidenceModel, QcIssueModel, QcResultModel, QcTaskModel

from .schema import QcResultDetailSchema, QcResultQueryParam


class QcResultService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def page(self, page_no: int, page_size: int, search: QcResultQueryParam) -> dict:
        stmt = (
            select(
                QcResultModel.id,
                QcResultModel.result_id,
                QcResultModel.score,
                QcResultModel.result_level,
                QcResultModel.risk_level,
                QcResultModel.summary,
                QcResultModel.confidence,
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.qn_status,
                DwdQnConversationModel.start_time,
                DimShopModel.shop_name,
                DimProductModel.product_id,
                DimProductModel.product_name,
                DimStaffModel.staff_name,
                DimCustomerModel.primary_taobao_account.label("customer_account"),
            )
            .select_from(QcResultModel)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .where(
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
        )

        scope_condition = await build_staff_scope_condition(self.auth)
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        if search.staff_id:
            stmt = stmt.where(DwdQnConversationModel.staff_id == search.staff_id)
        if search.shop_id:
            stmt = stmt.where(DwdQnConversationModel.shop_id == search.shop_id)
        if search.result_level:
            stmt = stmt.where(QcResultModel.result_level == search.result_level)
        if search.risk_level:
            stmt = stmt.where(QcResultModel.risk_level == search.risk_level)
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
                    DimCustomerModel.primary_taobao_account.like(keyword),
                )
            )

        stmt = stmt.order_by(desc(QcResultModel.created_time), desc(QcResultModel.id))
        return await paginate_query(self.auth.db, stmt, page_no, page_size)

    async def detail(self, id: int) -> QcResultDetailSchema:
        base_stmt = (
            select(
                QcResultModel.id,
                QcResultModel.result_id,
                QcResultModel.score,
                QcResultModel.result_level,
                QcResultModel.risk_level,
                QcResultModel.summary,
                QcResultModel.dimension_scores,
                QcResultModel.confidence,
                QcTaskModel.task_id,
                QcTaskModel.rule_version,
                QcTaskModel.prompt_version,
                QcTaskModel.model_name,
                DwdQnConversationModel.id.label("conversation_pk"),
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.staff_id,
                DwdQnConversationModel.qn_status,
                DwdQnConversationModel.start_time,
                DimShopModel.shop_name,
                DimProductModel.product_name,
                DimStaffModel.staff_name,
                DimCustomerModel.primary_taobao_account.label("customer_account"),
            )
            .select_from(QcResultModel)
            .join(QcTaskModel, QcResultModel.task_id == QcTaskModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .where(QcResultModel.id == id, QcResultModel.is_deleted == False)  # noqa: E712
        )
        scope_condition = await build_staff_scope_condition(self.auth)
        if scope_condition is not None:
            base_stmt = base_stmt.where(scope_condition)
        result = (await self.auth.db.execute(base_stmt)).mappings().first()
        if not result:
            raise CustomException(msg="质检结果不存在或无权查看")

        issue_stmt = (
            select(
                QcIssueModel.id,
                QcIssueModel.issue_id,
                QcIssueModel.rule_code,
                QcIssueModel.severity,
                QcIssueModel.title,
                QcIssueModel.reason,
                QcIssueModel.suggested_action,
                QcIssueModel.suggested_reply,
                QcIssueModel.deduction_score,
            )
            .where(QcIssueModel.result_id == id, QcIssueModel.is_deleted == False)  # noqa: E712
            .order_by(desc(QcIssueModel.deduction_score), QcIssueModel.id)
        )
        issues = (await self.auth.db.execute(issue_stmt)).mappings().all()
        issue_ids = [row["id"] for row in issues]

        evidences = []
        if issue_ids:
            evidence_stmt = (
                select(
                    QcIssueEvidenceModel.issue_id,
                    QcIssueEvidenceModel.evidence_id,
                    QcIssueEvidenceModel.evidence_text,
                    DwdQnMessageModel.message_id,
                    DwdQnMessageModel.speaker_type,
                    DwdQnMessageModel.speaker_account,
                    DwdQnMessageModel.content_text,
                    DwdQnMessageModel.message_time,
                )
                .join(DwdQnMessageModel, QcIssueEvidenceModel.message_id == DwdQnMessageModel.id)
                .where(
                    QcIssueEvidenceModel.issue_id.in_(issue_ids),
                    QcIssueEvidenceModel.is_deleted == False,  # noqa: E712
                )
                .order_by(QcIssueEvidenceModel.issue_id, DwdQnMessageModel.message_time)
            )
            evidences = [dict(row) for row in (await self.auth.db.execute(evidence_stmt)).mappings().all()]

        return QcResultDetailSchema(
            result=dict(result),
            issues=[dict(row) for row in issues],
            evidences=evidences,
        )
