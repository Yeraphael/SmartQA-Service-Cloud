import json
from datetime import datetime
from typing import Any

from sqlalchemy import case, desc, func, or_, select

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.common.access import build_staff_scope_condition
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel
from app.plugin.module_smartqa.models.dimension import DimCustomerModel, DimProductModel, DimShopModel, DimStaffModel
from app.plugin.module_smartqa.models.qc import QcIssueModel, QcResultModel, QcTaskModel


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

    async def opportunity_funnel(self) -> list[dict]:
        rows = await self.intent_customers(limit=200)
        stages = [
            ("consult", "有效咨询", len(rows)),
            ("need_clear", "需求明确", sum(1 for row in rows if row.get("need_summary") or row.get("need_type") not in {"unknown", ""})),
            ("quote", "报价/询价", sum(1 for row in rows if row.get("quote_given") or "报价" in (row.get("need_summary") or ""))),
            ("contact_asked", "已询问留资", sum(1 for row in rows if row.get("contact_requested"))),
            ("contact_provided", "客户已留资", sum(1 for row in rows if row.get("contact_provided"))),
            ("handoff", "可承接", sum(1 for row in rows if row.get("xianfa_handoff_status") in {"ready", "matched", "converted"})),
        ]
        total = stages[0][2] or 1
        return [{"stage": code, "label": label, "value": value, "rate": self._rate(value, total)} for code, label, value in stages]

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
