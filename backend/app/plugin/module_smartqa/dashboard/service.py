from sqlalchemy import case, desc, func, select

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.common.access import build_staff_scope_condition
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel
from app.plugin.module_smartqa.models.dimension import DimShopModel, DimStaffModel
from app.plugin.module_smartqa.models.qc import QcIssueModel, QcResultModel


class DashboardService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def overview(self) -> dict:
        scope_condition = await build_staff_scope_condition(self.auth)

        conversation_stmt = select(func.count(DwdQnConversationModel.id)).where(
            DwdQnConversationModel.is_deleted == False  # noqa: E712
        )
        result_stmt = (
            select(
                func.count(QcResultModel.id).label("qc_count"),
                func.avg(QcResultModel.score).label("avg_score"),
                func.sum(case((QcResultModel.result_level == "fail", 1), else_=0)).label("fail_count"),
                func.sum(case((QcResultModel.risk_level.in_(["high", "critical"]), 1), else_=0)).label("high_risk_count"),
            )
            .select_from(QcResultModel)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
        )
        issue_stmt = (
            select(func.count(QcIssueModel.id))
            .select_from(QcIssueModel)
            .join(QcResultModel, QcIssueModel.result_id == QcResultModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                QcIssueModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
        )

        if scope_condition is not None:
            conversation_stmt = conversation_stmt.where(scope_condition)
            result_stmt = result_stmt.where(scope_condition)
            issue_stmt = issue_stmt.where(scope_condition)

        conversation_count = (await self.auth.db.execute(conversation_stmt)).scalar() or 0
        result_row = (await self.auth.db.execute(result_stmt)).mappings().first() or {}
        issue_count = (await self.auth.db.execute(issue_stmt)).scalar() or 0

        return {
            "conversation_count": conversation_count,
            "qc_count": result_row.get("qc_count") or 0,
            "avg_score": round(float(result_row.get("avg_score") or 0), 2),
            "fail_count": result_row.get("fail_count") or 0,
            "high_risk_count": result_row.get("high_risk_count") or 0,
            "issue_count": issue_count,
        }

    async def staff_ranking(self, limit: int = 20) -> list[dict]:
        scope_condition = await build_staff_scope_condition(self.auth)
        stmt = (
            select(
                DimStaffModel.id.label("staff_id"),
                DimStaffModel.staff_name,
                DimStaffModel.primary_account,
                func.count(QcResultModel.id).label("qc_count"),
                func.avg(QcResultModel.score).label("avg_score"),
                func.sum(case((QcResultModel.risk_level.in_(["high", "critical"]), 1), else_=0)).label("high_risk_count"),
            )
            .select_from(DimStaffModel)
            .join(DwdQnConversationModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .join(QcResultModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                DimStaffModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
            )
            .group_by(DimStaffModel.id, DimStaffModel.staff_name, DimStaffModel.primary_account)
            .order_by(desc("avg_score"), desc("qc_count"))
            .limit(max(min(limit, 100), 1))
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        rows = (await self.auth.db.execute(stmt)).mappings().all()
        return [
            {
                **dict(row),
                "avg_score": round(float(row.get("avg_score") or 0), 2),
                "high_risk_count": row.get("high_risk_count") or 0,
            }
            for row in rows
        ]

    async def issue_distribution(self) -> list[dict]:
        scope_condition = await build_staff_scope_condition(self.auth)
        stmt = (
            select(
                QcIssueModel.rule_code,
                QcIssueModel.severity,
                func.count(QcIssueModel.id).label("issue_count"),
            )
            .select_from(QcIssueModel)
            .join(QcResultModel, QcIssueModel.result_id == QcResultModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                QcIssueModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
            .group_by(QcIssueModel.rule_code, QcIssueModel.severity)
            .order_by(desc("issue_count"))
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        rows = (await self.auth.db.execute(stmt)).mappings().all()
        return [dict(row) for row in rows]

    async def shop_distribution(self) -> list[dict]:
        scope_condition = await build_staff_scope_condition(self.auth)
        stmt = (
            select(
                DimShopModel.id.label("shop_id"),
                DimShopModel.shop_name,
                func.count(DwdQnConversationModel.id).label("conversation_count"),
            )
            .select_from(DwdQnConversationModel)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .where(DwdQnConversationModel.is_deleted == False)  # noqa: E712
            .group_by(DimShopModel.id, DimShopModel.shop_name)
            .order_by(desc("conversation_count"))
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        rows = (await self.auth.db.execute(stmt)).mappings().all()
        return [dict(row) for row in rows]
