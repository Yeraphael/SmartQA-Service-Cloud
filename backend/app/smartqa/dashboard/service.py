import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import case, desc, func, or_, select

from app.core.base_schema import AuthSchema
from app.smartqa.common.access import build_staff_scope_condition
from app.smartqa.models.conversation import DwdQnConversationModel
from app.smartqa.models.dimension import DimCustomerModel, DimProductModel, DimShopModel, DimStaffModel
from app.smartqa.models.ods import OdsImportBatchModel
from app.smartqa.models.qc import QcIssueModel, QcResultModel, QcTaskModel


class DashboardService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    DIMENSIONS: tuple[dict[str, Any], ...] = (
        {"key": "overall", "label": "综合表现", "aliases": ()},
        {"key": "response_efficiency", "label": "响应效率", "aliases": ("响应效率", "SQ01_RESPONSE_TIMELY", "SQ01", "response_efficiency", "response", "timely")},
        {"key": "service_attitude", "label": "服务态度", "aliases": ("服务态度", "SQ07_ATTITUDE_WARMTH", "SQ07", "attitude", "warmth", "service_attitude")},
        {"key": "professional_ability", "label": "专业能力", "aliases": ("专业能力", "SQ04_PRODUCT_PROFESSIONAL", "SQ04", "professional", "product_professional", "professional_ability")},
        {"key": "problem_solving", "label": "问题解决", "aliases": ("问题解决", "SQ05_SOLUTION_COMPLETE", "SQ05", "solution", "problem_solving", "problem")},
        {"key": "demand_mining", "label": "需求挖掘", "aliases": ("需求挖掘", "SQ03_NEED_PROBE", "SQ03", "need_probe", "demand_mining", "need")},
        {"key": "conversion_progress", "label": "成交推进", "aliases": ("成交推进", "SQ06_CONVERSION_CONTACT", "SQ06", "conversion", "contact", "conversion_progress")},
    )

    ISSUE_DIMENSION_MAP: dict[str, str] = {
        "SQ01_RESPONSE_TIMELY": "response_efficiency",
        "SQ02_RECEPTION_COMPLETE": "service_attitude",
        "SQ03_NEED_PROBE": "demand_mining",
        "SQ04_PRODUCT_PROFESSIONAL": "professional_ability",
        "SQ05_SOLUTION_COMPLETE": "problem_solving",
        "SQ06_CONVERSION_CONTACT": "conversion_progress",
        "SQ07_ATTITUDE_WARMTH": "service_attitude",
        "SQ08_OBJECTION_HANDLING": "conversion_progress",
        "SQ09_COMPLIANCE_RISK": "problem_solving",
        "SQ10_HANDOFF_RECORD": "conversion_progress",
    }

    async def boss_workbench(self) -> dict:
        """老板工作台聚合数据。

        工作台只返回当前页面需要的数据：顶部状态、核心指标、客服质检榜单、
        选中客服详情所需能力分、客服能力四象限、商品机会和近 7 日趋势。
        """

        scope_condition = await build_staff_scope_condition(self.auth)
        latest_batch = await self._latest_batch()
        result_rows = await self._quality_rows(scope_condition)
        issue_rows = await self._quality_issue_rows(scope_condition)
        intent_rows = await self.intent_customers(limit=200)
        products = await self.product_opportunities(limit=5)

        staff_items = self._build_staff_quality_items(result_rows, issue_rows, intent_rows)
        trend = self._build_trend(result_rows, intent_rows)
        overview = self._build_boss_overview(latest_batch, result_rows, staff_items, intent_rows)
        quadrant = self._build_quadrant(staff_items)

        return {
            "status": overview["status"],
            "metrics": overview["metrics"],
            "dimensions": [{"key": item["key"], "label": item["label"]} for item in self.DIMENSIONS],
            "staff_quality": staff_items,
            "quadrant": quadrant,
            "product_opportunities": products,
            "trend_7d": trend,
        }

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
        intent_rows = await self.intent_customers(limit=200)
        high_intent_count = sum(1 for row in intent_rows if row["intent_tier"] in {"H1", "H2"})
        h_customers = [row for row in intent_rows if row["intent_tier"] in {"H1", "H2"}]
        handoff_count = sum(
            1
            for row in h_customers
            if row.get("contact_requested") or row.get("contact_provided") or row.get("xianfa_handoff_status") in {"ready", "matched", "converted"}
        )
        contact_requested_count = sum(1 for row in intent_rows if row.get("contact_requested"))
        contact_provided_count = sum(1 for row in intent_rows if row.get("contact_provided"))

        return {
            "conversation_count": conversation_count,
            "qc_count": result_row.get("qc_count") or 0,
            "avg_score": round(float(result_row.get("avg_score") or 0), 2),
            "fail_count": result_row.get("fail_count") or 0,
            "high_risk_count": result_row.get("high_risk_count") or 0,
            "issue_count": issue_count,
            "high_intent_count": high_intent_count,
            "h_handoff_rate": self._rate(handoff_count, len(h_customers)),
            "contact_request_rate": self._rate(contact_requested_count, len(intent_rows)),
            "contact_success_rate": self._rate(contact_provided_count, contact_requested_count),
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
            .join(QcTaskModel, QcTaskModel.conversation_id == DwdQnConversationModel.id)
            .join(QcResultModel, QcResultModel.task_id == QcTaskModel.id)
            .where(
                DimStaffModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcTaskModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
            )
            .group_by(DimStaffModel.id, DimStaffModel.staff_name, DimStaffModel.primary_account)
            .order_by(desc("avg_score"), desc("qc_count"))
            .limit(max(min(limit, 100), 1))
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        rows = (await self.auth.db.execute(stmt)).mappings().all()
        intent_stats = self._staff_intent_stats(await self.intent_customers(limit=200))
        return [
            {
                **dict(row),
                "avg_score": round(float(row.get("avg_score") or 0), 2),
                "high_risk_count": row.get("high_risk_count") or 0,
                "h_customer_count": intent_stats.get(row["staff_id"], {}).get("h_customer_count", 0),
                "contact_request_rate": intent_stats.get(row["staff_id"], {}).get("contact_request_rate", 0.0),
                "contact_success_rate": intent_stats.get(row["staff_id"], {}).get("contact_success_rate", 0.0),
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

    async def staff_performance(self, staff_id: int | None = None, limit: int = 100) -> list[dict]:
        scope_condition = await build_staff_scope_condition(self.auth)
        stmt = (
            select(
                DimStaffModel.id.label("staff_id"),
                DimStaffModel.staff_name,
                DimStaffModel.primary_account,
                func.count(func.distinct(DwdQnConversationModel.id)).label("conversation_count"),
                func.count(func.distinct(QcResultModel.id)).label("qc_count"),
                func.avg(QcResultModel.score).label("avg_score"),
                func.count(func.distinct(QcIssueModel.id)).label("issue_count"),
                func.sum(case((QcResultModel.result_level == "fail", 1), else_=0)).label("fail_count"),
                func.sum(case((QcResultModel.risk_level.in_(["high", "critical"]), 1), else_=0)).label("high_risk_count"),
            )
            .select_from(DimStaffModel)
            .outerjoin(DwdQnConversationModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(QcTaskModel, QcTaskModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(QcResultModel, QcResultModel.task_id == QcTaskModel.id)
            .outerjoin(QcIssueModel, QcIssueModel.result_id == QcResultModel.id)
            .where(
                DimStaffModel.is_deleted == False,  # noqa: E712
                (DwdQnConversationModel.id.is_(None)) | (DwdQnConversationModel.is_deleted == False),  # noqa: E712
                (QcTaskModel.id.is_(None)) | (QcTaskModel.is_deleted == False),  # noqa: E712
                (QcResultModel.id.is_(None)) | (QcResultModel.is_deleted == False),  # noqa: E712
                (QcIssueModel.id.is_(None)) | (QcIssueModel.is_deleted == False),  # noqa: E712
            )
            .group_by(DimStaffModel.id, DimStaffModel.staff_name, DimStaffModel.primary_account)
            .order_by(desc("avg_score"), desc("qc_count"), desc("issue_count"))
            .limit(max(min(limit, 200), 1))
        )
        if staff_id:
            stmt = stmt.where(DimStaffModel.id == staff_id)
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        rows = (await self.auth.db.execute(stmt)).mappings().all()
        intent_rows = await self.intent_customers(limit=200)
        if staff_id:
            intent_rows = [row for row in intent_rows if row.get("staff_id") == staff_id]
        intent_stats = self._staff_intent_stats(intent_rows)
        return [
            {
                **dict(row),
                "avg_score": round(float(row.get("avg_score") or 0), 2),
                "issue_count": row.get("issue_count") or 0,
                "fail_count": row.get("fail_count") or 0,
                "high_risk_count": row.get("high_risk_count") or 0,
                "h_customer_count": intent_stats.get(row["staff_id"], {}).get("h_customer_count", 0),
                "contact_request_rate": intent_stats.get(row["staff_id"], {}).get("contact_request_rate", 0.0),
                "contact_success_rate": intent_stats.get(row["staff_id"], {}).get("contact_success_rate", 0.0),
            }
            for row in rows
        ]

    async def improvements(self, limit: int = 20, staff_id: int | None = None) -> dict:
        scope_condition = await build_staff_scope_condition(self.auth)
        limit = max(min(limit, 100), 1)

        summary_stmt = (
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
        frequent_stmt = (
            select(
                QcIssueModel.rule_code,
                QcIssueModel.severity,
                QcIssueModel.title,
                QcIssueModel.reason,
                QcIssueModel.suggested_action,
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
            .group_by(
                QcIssueModel.rule_code,
                QcIssueModel.severity,
                QcIssueModel.title,
                QcIssueModel.reason,
                QcIssueModel.suggested_action,
            )
            .order_by(desc("issue_count"))
            .limit(limit)
        )
        replies_stmt = (
            select(
                QcIssueModel.rule_code,
                QcIssueModel.title,
                QcIssueModel.suggested_reply,
                func.count(QcIssueModel.id).label("issue_count"),
            )
            .select_from(QcIssueModel)
            .join(QcResultModel, QcIssueModel.result_id == QcResultModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                QcIssueModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcIssueModel.suggested_reply.is_not(None),
                QcIssueModel.suggested_reply != "",
            )
            .group_by(QcIssueModel.rule_code, QcIssueModel.title, QcIssueModel.suggested_reply)
            .order_by(desc("issue_count"))
            .limit(limit)
        )
        risk_stmt = (
            select(
                QcResultModel.id.label("result_id"),
                QcResultModel.score,
                QcResultModel.risk_level,
                QcResultModel.summary,
                DwdQnConversationModel.id.label("conversation_pk"),
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.start_time,
                DimProductModel.product_name,
                DimCustomerModel.primary_taobao_account.label("customer_account"),
            )
            .select_from(QcResultModel)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .where(
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcResultModel.risk_level.in_(["high", "critical"]),
            )
            .order_by(desc(QcResultModel.created_time), desc(QcResultModel.id))
            .limit(limit)
        )

        if scope_condition is not None:
            summary_stmt = summary_stmt.where(scope_condition)
            frequent_stmt = frequent_stmt.where(scope_condition)
            replies_stmt = replies_stmt.where(scope_condition)
            risk_stmt = risk_stmt.where(scope_condition)
        if staff_id:
            summary_stmt = summary_stmt.where(DwdQnConversationModel.staff_id == staff_id)
            frequent_stmt = frequent_stmt.where(DwdQnConversationModel.staff_id == staff_id)
            replies_stmt = replies_stmt.where(DwdQnConversationModel.staff_id == staff_id)
            risk_stmt = risk_stmt.where(DwdQnConversationModel.staff_id == staff_id)

        return {
            "issue_summary": [dict(row) for row in (await self.auth.db.execute(summary_stmt)).mappings().all()],
            "frequent_issues": [dict(row) for row in (await self.auth.db.execute(frequent_stmt)).mappings().all()],
            "suggested_replies": [dict(row) for row in (await self.auth.db.execute(replies_stmt)).mappings().all()],
            "recent_high_risk": [dict(row) for row in (await self.auth.db.execute(risk_stmt)).mappings().all()],
        }

    async def intent_customers(self, limit: int = 50, keyword: str | None = None, tier: str | None = None) -> list[dict]:
        scope_condition = await build_staff_scope_condition(self.auth)
        stmt = (
            select(
                QcResultModel.id.label("result_id"),
                QcResultModel.score.label("staff_quality_score"),
                QcResultModel.risk_level,
                QcResultModel.summary,
                QcTaskModel.response_json,
                DwdQnConversationModel.id.label("conversation_pk"),
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.start_time,
                DwdQnConversationModel.end_time,
                DwdQnConversationModel.first_response_seconds,
                DwdQnConversationModel.avg_response_seconds,
                DimStaffModel.id.label("staff_id"),
                DimStaffModel.staff_name,
                DimCustomerModel.id.label("customer_id"),
                DimCustomerModel.primary_taobao_account.label("customer_account"),
                DimCustomerModel.buyer_wangwang_masked.label("customer_alias_masked"),
                DimShopModel.id.label("shop_id"),
                DimShopModel.shop_name,
                DimProductModel.id.label("product_pk"),
                DimProductModel.product_id,
                DimProductModel.product_name,
            )
            .select_from(QcResultModel)
            .join(QcTaskModel, QcResultModel.task_id == QcTaskModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimCustomerModel, DwdQnConversationModel.customer_id == DimCustomerModel.id)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .where(
                QcResultModel.is_deleted == False,  # noqa: E712
                QcTaskModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcTaskModel.status == "success",
            )
            .order_by(desc(QcResultModel.created_time), desc(QcResultModel.id))
            .limit(max(min(limit, 200), 1))
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    DimCustomerModel.primary_taobao_account.like(like),
                    DimCustomerModel.buyer_wangwang_masked.like(like),
                    DimProductModel.product_name.like(like),
                    DimStaffModel.staff_name.like(like),
                )
            )

        rows = (await self.auth.db.execute(stmt)).mappings().all()
        out = [self._intent_row(dict(row)) for row in rows]
        if tier:
            out = [row for row in out if row["intent_tier"] == tier]
        return sorted(out, key=lambda row: (self._tier_rank(row["intent_tier"]), -int(row.get("intent_score") or 0), row.get("silent_hours") or 0))

    async def product_opportunities(self, limit: int = 20) -> list[dict]:
        rows = await self.intent_customers(limit=200)
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row.get("product_pk") or row.get("product_id") or row.get("product_name") or "unknown")
            item = grouped.setdefault(
                key,
                {
                    "product_id": row.get("product_id"),
                    "product_name": row.get("product_name") or "未知商品",
                    "conversation_count": 0,
                    "h_customer_count": 0,
                    "avg_intent_score": 0,
                    "custom_count": 0,
                    "bulk_count": 0,
                    "price_sensitive_count": 0,
                },
            )
            item["conversation_count"] += 1
            score = int(row.get("intent_score") or 0)
            item["avg_intent_score"] += score
            if row.get("intent_tier") in {"H1", "H2"}:
                item["h_customer_count"] += 1
            tags = set(row.get("tags") or [])
            need_type = str(row.get("need_type") or "")
            if "CUSTOMER_CUSTOM" in tags or "定制" in need_type or need_type == "custom":
                item["custom_count"] += 1
            if "CUSTOMER_BULK" in tags or "批量" in need_type or need_type == "bulk":
                item["bulk_count"] += 1
            if "CUSTOMER_PRICE_SENSITIVE" in tags or row.get("budget_status") == "price_sensitive":
                item["price_sensitive_count"] += 1
        result = []
        for item in grouped.values():
            count = item["conversation_count"] or 1
            item["avg_intent_score"] = round(item["avg_intent_score"] / count, 2)
            item["h_customer_rate"] = self._rate(item["h_customer_count"], count)
            result.append(item)
        return sorted(result, key=lambda item: (item["h_customer_count"], item["conversation_count"]), reverse=True)[: max(min(limit, 100), 1)]

    @staticmethod
    def _rate(numerator: int | float, denominator: int | float) -> float:
        if not denominator:
            return 0.0
        return round(float(numerator) * 100 / float(denominator), 2)

    @staticmethod
    def _tier_rank(tier: str) -> int:
        return {"H1": 1, "H2": 2, "H3": 3, "H4": 4, "L": 5}.get(tier or "", 9)

    def _staff_intent_stats(self, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        stats: dict[int, dict[str, Any]] = {}
        for row in rows:
            staff_id = row.get("staff_id")
            if not staff_id:
                continue
            item = stats.setdefault(
                int(staff_id),
                {
                    "qc_count": 0,
                    "h_customer_count": 0,
                    "contact_requested_count": 0,
                    "contact_provided_count": 0,
                },
            )
            item["qc_count"] += 1
            if row.get("intent_tier") in {"H1", "H2"}:
                item["h_customer_count"] += 1
            if row.get("contact_requested"):
                item["contact_requested_count"] += 1
            if row.get("contact_provided"):
                item["contact_provided_count"] += 1
        for item in stats.values():
            item["contact_request_rate"] = self._rate(item["contact_requested_count"], item["qc_count"])
            item["contact_success_rate"] = self._rate(item["contact_provided_count"], item["contact_requested_count"])
        return stats

    def _intent_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = row.get("response_json") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        intent = payload.get("customer_intent_detail") or {}
        staff_quality = payload.get("staff_quality") or {}
        contact = intent.get("contact_status") or {}
        reasons = intent.get("intent_reasons") or []
        evidence_count = sum(len(reason.get("evidence_message_ids") or []) for reason in reasons)
        last_time = row.get("end_time") or row.get("start_time")
        silent_hours = None
        if isinstance(last_time, datetime):
            silent_hours = round(max((datetime.now() - last_time).total_seconds(), 0) / 3600, 1)
        return {
            **{k: v for k, v in row.items() if k != "response_json"},
            "staff_quality_score": staff_quality.get("score") or row.get("staff_quality_score"),
            "intent_score": intent.get("intent_score") or 0,
            "intent_tier": intent.get("intent_tier") or self._tier_from_score(intent.get("intent_score") or 0),
            "lifecycle_stage": intent.get("lifecycle_stage") or "CL01",
            "need_type": intent.get("need_type") or "unknown",
            "need_summary": intent.get("need_summary") or row.get("summary") or "",
            "intent_reasons": reasons,
            "intent_reason_text": "、".join(reason.get("reason_text") or reason.get("reason_code") or "" for reason in reasons) or "暂无模型原因",
            "intent_evidence_message_ids": [
                msg_id
                for reason in reasons
                for msg_id in (reason.get("evidence_message_ids") or [])
            ],
            "evidence_count": evidence_count,
            "missing_infos": intent.get("missing_infos") or [],
            "tags": intent.get("tags") or [],
            "contact_requested": bool(contact.get("contact_requested")),
            "contact_provided": bool(contact.get("contact_provided")),
            "contact_type": contact.get("contact_type"),
            "xianfa_handoff_status": contact.get("xianfa_handoff_status") or "none",
            "next_action": intent.get("next_action") or "复盘会话并补齐客户下一步动作",
            "suggested_reply": intent.get("suggested_reply") or "",
            "quote_given": bool(payload.get("quote_given") or staff_quality.get("dimension_scores", {}).get("SQ06_conversion_contact")),
            "silent_hours": silent_hours,
            "risk_flags": self._risk_flags(intent, contact, row.get("risk_level")),
        }

    @staticmethod
    def _tier_from_score(score: int | float) -> str:
        score = int(score or 0)
        if score >= 85:
            return "H1"
        if score >= 70:
            return "H2"
        if score >= 50:
            return "H3"
        if score >= 30:
            return "H4"
        return "L"

    @staticmethod
    def _risk_flags(intent: dict[str, Any], contact: dict[str, Any], risk_level: str | None) -> list[str]:
        flags: list[str] = []
        tier = intent.get("intent_tier") or ""
        if tier in {"H1", "H2"} and not contact.get("contact_requested"):
            flags.append("高意向未留资")
        if contact.get("contact_provided") and contact.get("xianfa_handoff_status") not in {"ready", "matched", "converted"}:
            flags.append("留资未承接")
        if risk_level in {"high", "critical"}:
            flags.append("服务高风险")
        return flags

    async def _latest_batch(self) -> OdsImportBatchModel | None:
        stmt = (
            select(OdsImportBatchModel)
            .where(OdsImportBatchModel.is_deleted == False)  # noqa: E712
            .order_by(desc(OdsImportBatchModel.finished_at), desc(OdsImportBatchModel.created_time), desc(OdsImportBatchModel.id))
            .limit(1)
        )
        return (await self.auth.db.execute(stmt)).scalars().first()

    async def _quality_rows(self, scope_condition: Any | None) -> list[dict[str, Any]]:
        stmt = (
            select(
                QcResultModel.id.label("result_pk"),
                QcResultModel.score,
                QcResultModel.result_level,
                QcResultModel.risk_level,
                QcResultModel.summary,
                QcResultModel.dimension_scores,
                QcResultModel.created_time.label("result_created_time"),
                QcTaskModel.finished_at.label("task_finished_at"),
                QcTaskModel.response_json,
                DwdQnConversationModel.id.label("conversation_pk"),
                DwdQnConversationModel.conversation_id,
                DwdQnConversationModel.start_time,
                DwdQnConversationModel.end_time,
                DwdQnConversationModel.message_count,
                DwdQnConversationModel.first_response_seconds,
                DwdQnConversationModel.avg_response_seconds,
                DimStaffModel.id.label("staff_id"),
                DimStaffModel.staff_name,
                DimStaffModel.primary_account,
                DimShopModel.shop_name,
                DimProductModel.product_id,
                DimProductModel.product_name,
            )
            .select_from(QcResultModel)
            .join(QcTaskModel, QcResultModel.task_id == QcTaskModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .outerjoin(DimStaffModel, DwdQnConversationModel.staff_id == DimStaffModel.id)
            .outerjoin(DimShopModel, DwdQnConversationModel.shop_id == DimShopModel.id)
            .outerjoin(DimProductModel, DwdQnConversationModel.product_id == DimProductModel.id)
            .where(
                QcResultModel.is_deleted == False,  # noqa: E712
                QcTaskModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
                QcTaskModel.status == "success",
            )
            .order_by(desc(QcResultModel.created_time), desc(QcResultModel.id))
            .limit(2000)
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        return [dict(row) for row in (await self.auth.db.execute(stmt)).mappings().all()]

    async def _quality_issue_rows(self, scope_condition: Any | None) -> list[dict[str, Any]]:
        stmt = (
            select(
                QcResultModel.id.label("result_pk"),
                DwdQnConversationModel.staff_id,
                QcIssueModel.rule_code,
                QcIssueModel.severity,
                QcIssueModel.title,
                QcIssueModel.reason,
                QcIssueModel.suggested_action,
                QcIssueModel.deduction_score,
            )
            .select_from(QcIssueModel)
            .join(QcResultModel, QcIssueModel.result_id == QcResultModel.id)
            .join(DwdQnConversationModel, QcResultModel.conversation_id == DwdQnConversationModel.id)
            .where(
                QcIssueModel.is_deleted == False,  # noqa: E712
                QcResultModel.is_deleted == False,  # noqa: E712
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(QcIssueModel.created_time), desc(QcIssueModel.id))
            .limit(5000)
        )
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)
        return [dict(row) for row in (await self.auth.db.execute(stmt)).mappings().all()]

    def _build_boss_overview(
        self,
        latest_batch: OdsImportBatchModel | None,
        rows: list[dict[str, Any]],
        staff_items: list[dict[str, Any]],
        intent_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        score_values = [float(row.get("score") or 0) for row in rows if row.get("score") is not None]
        avg_response_values = [int(row.get("avg_response_seconds") or 0) for row in rows if row.get("avg_response_seconds")]
        ai_finished_at = max((row.get("task_finished_at") or row.get("result_created_time") for row in rows if row.get("task_finished_at") or row.get("result_created_time")), default=None)
        data_date = max((row.get("start_time").date() for row in rows if isinstance(row.get("start_time"), datetime)), default=None)
        high_intent_pending = self._pending_intent_count(intent_rows)
        need_attention_staff = sum(1 for row in staff_items if row.get("overall_score", 0) < 80)
        status_text = self._system_status(latest_batch, rows)

        return {
            "status": {
                "data_date": data_date,
                "rpa_fetch_time": latest_batch.finished_at if latest_batch else None,
                "ai_finished_time": ai_finished_at,
                "analyzed_conversation_count": len({row.get("conversation_pk") for row in rows if row.get("conversation_pk")}),
                "covered_staff_count": len({row.get("staff_id") for row in rows if row.get("staff_id")}),
                "system_status": status_text,
            },
            "metrics": {
                "service_quality_score": self._avg(score_values),
                "high_risk_conversation_count": sum(1 for row in rows if row.get("risk_level") in {"high", "critical"}),
                "need_attention_staff_count": need_attention_staff,
                "high_intent_pending_count": high_intent_pending,
                "avg_response_seconds": round(sum(avg_response_values) / len(avg_response_values)) if avg_response_values else 0,
                "conversation_count": len({row.get("conversation_pk") for row in rows if row.get("conversation_pk")}),
            },
        }

    def _build_staff_quality_items(
        self,
        rows: list[dict[str, Any]],
        issue_rows: list[dict[str, Any]],
        intent_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        staff_bucket: dict[int, dict[str, Any]] = {}
        result_issue_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
        staff_issue_titles: dict[int, Counter[str]] = defaultdict(Counter)
        staff_issue_dimension: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for issue in issue_rows:
            result_pk = issue.get("result_pk")
            staff_id = issue.get("staff_id")
            if result_pk:
                result_issue_map[int(result_pk)].append(issue)
            if staff_id:
                title = issue.get("title") or issue.get("rule_code") or "服务问题"
                staff_issue_titles[int(staff_id)][title] += 1
                dimension_key = self.ISSUE_DIMENSION_MAP.get(str(issue.get("rule_code") or ""), "problem_solving")
                staff_issue_dimension[int(staff_id)][dimension_key] += int(issue.get("deduction_score") or 0)

        intent_stats = self._staff_intent_stats(intent_rows)

        for row in rows:
            staff_id = row.get("staff_id")
            if not staff_id:
                continue
            staff_id = int(staff_id)
            item = staff_bucket.setdefault(
                staff_id,
                {
                    "staff_id": staff_id,
                    "staff_name": row.get("staff_name") or "未绑定客服",
                    "primary_account": row.get("primary_account") or "",
                    "conversation_count": 0,
                    "qc_count": 0,
                    "score_sum": 0.0,
                    "high_risk_count": 0,
                    "dimension_sum": defaultdict(float),
                    "dimension_count": defaultdict(int),
                    "trend_bucket": defaultdict(list),
                    "shop_names": Counter(),
                },
            )
            score = float(row.get("score") or 0)
            item["qc_count"] += 1
            item["conversation_count"] += 1
            item["score_sum"] += score
            if row.get("risk_level") in {"high", "critical"}:
                item["high_risk_count"] += 1
            if row.get("shop_name"):
                item["shop_names"][row["shop_name"]] += 1

            dimension_scores = self._extract_dimension_scores(row, result_issue_map.get(int(row.get("result_pk") or 0), []), score)
            for key, value in dimension_scores.items():
                item["dimension_sum"][key] += float(value)
                item["dimension_count"][key] += 1

            trend_date = row.get("start_time") or row.get("result_created_time")
            if isinstance(trend_date, datetime):
                item["trend_bucket"][trend_date.date()].append(score)

        staff_items: list[dict[str, Any]] = []
        for staff_id, item in staff_bucket.items():
            qc_count = int(item["qc_count"] or 0)
            overall_score = round(float(item["score_sum"]) / qc_count, 1) if qc_count else 0.0
            dimensions = {"overall": overall_score}
            for dim in self.DIMENSIONS:
                key = dim["key"]
                if key == "overall":
                    continue
                if item["dimension_count"].get(key):
                    value = item["dimension_sum"][key] / item["dimension_count"][key]
                else:
                    deduction = staff_issue_dimension.get(staff_id, {}).get(key, 0)
                    value = max(overall_score - min(deduction / max(qc_count, 1), 18), 0)
                dimensions[key] = round(float(value), 1)

            trend = self._staff_trend(item["trend_bucket"])
            main_issue = staff_issue_titles.get(staff_id, Counter()).most_common(1)
            top_shop = item["shop_names"].most_common(1)
            staff_items.append(
                {
                    "staff_id": staff_id,
                    "staff_name": item["staff_name"],
                    "primary_account": item["primary_account"],
                    "role_label": "客服专员",
                    "shop_name": top_shop[0][0] if top_shop else None,
                    "group_name": None,
                    "qc_count": qc_count,
                    "conversation_count": item["conversation_count"],
                    "overall_score": overall_score,
                    "dimensions": dimensions,
                    "high_risk_count": item["high_risk_count"],
                    "pending_intent_count": intent_stats.get(staff_id, {}).get("h_customer_count", 0),
                    "main_issue": main_issue[0][0] if main_issue else "暂无突出问题",
                    "trend": trend,
                }
            )

        return sorted(staff_items, key=lambda row: (row["overall_score"], row["qc_count"]), reverse=True)

    def _extract_dimension_scores(self, row: dict[str, Any], issues: list[dict[str, Any]], fallback_score: float) -> dict[str, float]:
        raw_scores = row.get("dimension_scores") or {}
        payload = row.get("response_json") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        staff_quality = payload.get("staff_quality") or {}
        raw_scores = raw_scores or staff_quality.get("dimension_scores") or payload.get("dimension_scores") or {}
        if isinstance(raw_scores, str):
            try:
                raw_scores = json.loads(raw_scores)
            except json.JSONDecodeError:
                raw_scores = {}

        result: dict[str, float] = {}
        for dim in self.DIMENSIONS:
            key = dim["key"]
            if key == "overall":
                continue
            value = self._dimension_value(raw_scores, dim["aliases"])
            if value is not None:
                result[key] = value

        if len(result) < len(self.DIMENSIONS) - 1:
            deduction_map: dict[str, int] = defaultdict(int)
            for issue in issues:
                dim_key = self.ISSUE_DIMENSION_MAP.get(str(issue.get("rule_code") or ""), "problem_solving")
                deduction_map[dim_key] += int(issue.get("deduction_score") or 0)
            for dim in self.DIMENSIONS:
                key = dim["key"]
                if key == "overall" or key in result:
                    continue
                result[key] = max(min(float(fallback_score) - min(deduction_map.get(key, 0), 30) * 0.65, 100), 0)
        return result

    @staticmethod
    def _dimension_value(raw_scores: Any, aliases: tuple[str, ...]) -> float | None:
        if not isinstance(raw_scores, dict):
            return None
        normalized = {str(k).lower(): v for k, v in raw_scores.items()}
        for alias in aliases:
            lookup = alias.lower()
            for raw_key, raw_value in normalized.items():
                if lookup == raw_key or lookup in raw_key:
                    if isinstance(raw_value, dict):
                        raw_value = raw_value.get("score") or raw_value.get("value")
                    try:
                        return round(float(raw_value), 1)
                    except (TypeError, ValueError):
                        continue
        return None

    def _build_quadrant(self, staff_items: list[dict[str, Any]]) -> dict[str, Any]:
        points = []
        for row in staff_items:
            dimensions = row.get("dimensions") or {}
            service_efficiency = self._avg([
                dimensions.get("response_efficiency", 0),
                dimensions.get("problem_solving", 0),
                dimensions.get("conversion_progress", 0),
            ])
            quality_score = self._avg([
                row.get("overall_score", 0),
                dimensions.get("service_attitude", 0),
                dimensions.get("professional_ability", 0),
                dimensions.get("demand_mining", 0),
            ])
            points.append(
                {
                    "staff_id": row["staff_id"],
                    "staff_name": row["staff_name"],
                    "x": service_efficiency,
                    "y": quality_score,
                    "score": row.get("overall_score", 0),
                    "status": self._score_status(row.get("overall_score", 0)),
                }
            )
        return {
            "x_axis": "服务效率分",
            "y_axis": "服务质量分",
            "points": points,
        }

    def _build_trend(self, rows: list[dict[str, Any]], intent_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        today = self._latest_business_date(rows) or date.today()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        score_bucket: dict[date, list[float]] = defaultdict(list)
        risk_bucket: Counter[date] = Counter()
        conversation_bucket: set[tuple[date, int]] = set()

        for row in rows:
            current = row.get("start_time") or row.get("result_created_time")
            if not isinstance(current, datetime):
                continue
            day = current.date()
            if day not in days:
                continue
            score_bucket[day].append(float(row.get("score") or 0))
            if row.get("risk_level") in {"high", "critical"}:
                risk_bucket[day] += 1
            if row.get("conversation_pk"):
                conversation_bucket.add((day, int(row["conversation_pk"])))

        intent_bucket: Counter[date] = Counter()
        for row in intent_rows:
            start_time = row.get("start_time")
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time)
                except ValueError:
                    start_time = None
            if isinstance(start_time, datetime) and start_time.date() in days and self._is_pending_high_intent(row):
                intent_bucket[start_time.date()] += 1

        return [
            {
                "date": day.strftime("%m-%d"),
                "quality_score": self._avg(score_bucket.get(day, [])),
                "high_risk_count": risk_bucket.get(day, 0),
                "pending_intent_count": intent_bucket.get(day, 0),
                "conversation_count": sum(1 for item in conversation_bucket if item[0] == day),
            }
            for day in days
        ]

    @staticmethod
    def _latest_business_date(rows: list[dict[str, Any]]) -> date | None:
        dates = [
            value.date()
            for row in rows
            for value in [row.get("start_time"), row.get("result_created_time")]
            if isinstance(value, datetime)
        ]
        return max(dates) if dates else None

    def _staff_trend(self, bucket: dict[date, list[float]]) -> list[dict[str, Any]]:
        today = max(bucket.keys(), default=date.today())
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        return [{"date": day.strftime("%m-%d"), "score": self._avg(bucket.get(day, []))} for day in days]

    @staticmethod
    def _avg(values: list[int | float]) -> float:
        values = [float(value) for value in values if value is not None]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 1)

    @staticmethod
    def _pending_intent_count(rows: list[dict[str, Any]]) -> int:
        return sum(1 for row in rows if DashboardService._is_pending_high_intent(row))

    @staticmethod
    def _is_pending_high_intent(row: dict[str, Any]) -> bool:
        return row.get("intent_tier") in {"H1", "H2"} and not (
            row.get("contact_requested")
            or row.get("contact_provided")
            or row.get("xianfa_handoff_status") in {"ready", "matched", "converted"}
        )

    @staticmethod
    def _system_status(latest_batch: OdsImportBatchModel | None, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "待分析"
        if latest_batch and latest_batch.status not in {"success", "completed"}:
            return "处理中" if latest_batch.status in {"pending", "running"} else "部分异常"
        return "正常"

    @staticmethod
    def _score_status(score: int | float) -> str:
        score = float(score or 0)
        if score >= 90:
            return "优秀"
        if score >= 80:
            return "良好"
        if score >= 70:
            return "需关注"
        return "需改进"
