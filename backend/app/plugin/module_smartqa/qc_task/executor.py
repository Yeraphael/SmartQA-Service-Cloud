"""AI质检任务执行引擎。"""

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.config.setting import settings
from app.plugin.module_smartqa.models.conversation import DwdQnConversationModel, DwdQnMessageModel
from app.plugin.module_smartqa.models.qc import (
    ModelCallLogModel,
    QcIssueEvidenceModel,
    QcIssueModel,
    QcPromptTemplateModel,
    QcResultModel,
    QcRuleModel,
    QcRuleVersionModel,
    QcTaskModel,
)

from .ai_client import QwenClient


class QcTaskExecutor:
    """AI质检任务执行器。"""

    def __init__(self, auth: AuthSchema | None = None):
        self.auth = auth
        self._ai_client: QwenClient | None = None

    @property
    def ai_client(self) -> QwenClient:
        if self._ai_client is None:
            self._ai_client = QwenClient()
        return self._ai_client

    async def create_tasks(
        self,
        session: AsyncSession,
        conversation_ids: list[int],
        rule_version: str,
        model_name: str | None = None,
    ) -> list[QcTaskModel]:
        """为指定会话创建质检任务。"""
        version_stmt = select(QcRuleVersionModel).where(
            QcRuleVersionModel.rule_version == rule_version,
            QcRuleVersionModel.status == "active",
            QcRuleVersionModel.is_deleted == False,  # noqa: E712
        )
        version_result = await session.execute(version_stmt)
        version = version_result.scalar_one_or_none()
        if not version:
            raise CustomException("规则版本不存在或未激活")

        conv_stmt = select(DwdQnConversationModel).where(
            DwdQnConversationModel.id.in_(conversation_ids),
            DwdQnConversationModel.is_deleted == False,  # noqa: E712
        )
        conv_result = await session.execute(conv_stmt)
        conversations = list(conv_result.scalars().all())

        tasks = []
        for conv in conversations:
            task_id = f"task_{conv.id}_{self._short_hash(conv.conversation_id + conv.data_hash + rule_version + version.prompt_version)}"

            existing_task_stmt = select(QcTaskModel).where(
                QcTaskModel.conversation_id == conv.id,
                QcTaskModel.conversation_data_hash == conv.data_hash,
                QcTaskModel.rule_version == rule_version,
                QcTaskModel.prompt_version == version.prompt_version,
                QcTaskModel.is_deleted == False,  # noqa: E712
            )
            existing_task_result = await session.execute(existing_task_stmt)
            existing_task = existing_task_result.scalar_one_or_none()

            if existing_task and existing_task.status in ["pending", "running", "success"]:
                continue

            task = QcTaskModel(
                task_id=task_id,
                conversation_id=conv.id,
                conversation_data_hash=conv.data_hash,
                rule_version=rule_version,
                prompt_version=version.prompt_version,
                model_name=model_name or settings.SMARTQA_ALI_MODEL_NAME,
                status="pending",
                tenant_id=self.auth.tenant_id if self.auth else None,
                created_id=self.auth.user.id if self.auth and self.auth.user else None,
            )
            session.add(task)
            tasks.append(task)

        await session.flush()
        return tasks

    async def execute_task(self, session: AsyncSession, task_id: int) -> dict:
        """执行单个质检任务。"""
        task_stmt = select(QcTaskModel).where(
            QcTaskModel.id == task_id,
            QcTaskModel.is_deleted == False,  # noqa: E712
        )
        task_result = await session.execute(task_stmt)
        task = task_result.scalar_one_or_none()
        if not task:
            raise CustomException("任务不存在")

        if task.status == "success":
            raise CustomException("任务已完成")

        task.status = "running"
        task.started_at = datetime.now()
        await session.flush()

        try:
            conversation_data = await self._build_conversation_data(session, task.conversation_id)
            prompt_content = await self._build_prompt(session, task, conversation_data)

            call_id = f"call_{task.task_id}_{int(datetime.now().timestamp())}"
            call_log = ModelCallLogModel(
                call_id=call_id,
                task_id=task.id,
                model_name=task.model_name,
                request_payload={"conversation_id": conversation_data["conversation_id"]},
                tenant_id=self.auth.tenant_id if self.auth else None,
            )
            session.add(call_log)
            await session.flush()

            ai_response = await self.ai_client.call_model(
                model_name=task.model_name,
                prompt=prompt_content,
            )

            call_log.response_payload = ai_response.get("response")
            call_log.raw_response_text = ai_response.get("raw_text")
            call_log.input_tokens = ai_response.get("input_tokens")
            call_log.output_tokens = ai_response.get("output_tokens")
            call_log.success = ai_response.get("success", False)
            call_log.error_message = ai_response.get("error")

            if not ai_response.get("success"):
                raise Exception(ai_response.get("error", "AI调用失败"))

            result_json = self._parse_ai_response(ai_response.get("raw_text", ""))

            task.response_json = result_json
            task.status = "success"
            task.finished_at = datetime.now()

            await self._save_result(session, task, result_json, conversation_data)

            await session.flush()

            return {
                "task_id": task.task_id,
                "status": "success",
                "result": result_json,
            }

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.finished_at = datetime.now()
            await session.flush()
            raise CustomException(f"质检执行失败: {str(e)}")

    async def _build_conversation_data(self, session: AsyncSession, conversation_id: int) -> dict:
        """构建会话数据用于AI质检。"""
        conv_stmt = select(DwdQnConversationModel).where(
            DwdQnConversationModel.id == conversation_id,
            DwdQnConversationModel.is_deleted == False,  # noqa: E712
        )
        conv_result = await session.execute(conv_stmt)
        conv = conv_result.scalar_one_or_none()
        if not conv:
            raise CustomException("会话不存在")

        msg_stmt = (
            select(DwdQnMessageModel)
            .where(
                DwdQnMessageModel.conversation_id == conversation_id,
                DwdQnMessageModel.is_deleted == False,  # noqa: E712
            )
            .order_by(DwdQnMessageModel.message_time)
        )
        msg_result = await session.execute(msg_stmt)
        messages = list(msg_result.scalars().all())

        return {
            "conversation_id": conv.conversation_id,
            "qn_status": conv.qn_status,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "speaker_type": msg.speaker_type,
                    "speaker_account": msg.speaker_account,
                    "content": msg.content_text or "",
                    "time": msg.message_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for msg in messages
            ],
        }

    async def _build_prompt(self, session: AsyncSession, task: QcTaskModel, conversation_data: dict) -> str:
        """构建AI质检Prompt。"""
        template_stmt = select(QcPromptTemplateModel).where(
            QcPromptTemplateModel.prompt_version == task.prompt_version,
            QcPromptTemplateModel.is_deleted == False,  # noqa: E712
        )
        template_result = await session.execute(template_stmt)
        template = template_result.scalar_one_or_none()
        if not template:
            raise CustomException("Prompt模板不存在")

        version_stmt = select(QcRuleVersionModel).where(
            QcRuleVersionModel.rule_version == task.rule_version,
            QcRuleVersionModel.is_deleted == False,  # noqa: E712
        )
        version_result = await session.execute(version_stmt)
        version = version_result.scalar_one_or_none()

        messages_text = "\n".join(
            [
                f"[{msg['message_id']}][{msg['time']}][{msg['speaker_type']}][{msg['speaker_account']}] {msg['content']}"
                for msg in conversation_data["messages"]
            ]
        )

        rules_text = "\n".join(
            [
                f"- {rule_code}: {rule_info['rule_name']} (扣分: {rule_info['deduction_score']}, 严重程度: {rule_info['severity']})\n  判断标准: {rule_info['judgment_standard']}"
                for rule_code, rule_info in (version.rule_snapshot or {}).items()
            ]
        )

        prompt = (
            template.template_content
            .replace("{conversation_id}", conversation_data["conversation_id"])
            .replace("{qn_status}", conversation_data.get("qn_status", "") or "")
            .replace("{messages}", messages_text)
            .replace("{rules}", rules_text)
        )

        return prompt

    def _parse_ai_response(self, raw_text: str) -> dict:
        """解析AI响应为JSON结构。"""
        try:
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            result = json.loads(cleaned_text)
            return result
        except json.JSONDecodeError as e:
            raise Exception(f"AI响应JSON解析失败: {str(e)}")

    async def _save_result(self, session: AsyncSession, task: QcTaskModel, result_json: dict, conversation_data: dict) -> None:
        """保存质检结果到数据库。"""
        result_id = f"res_{task.task_id}"

        old_result_stmt = select(QcResultModel).where(
            QcResultModel.task_id == task.id,
            QcResultModel.is_deleted == False,  # noqa: E712
        )
        old_result = (await session.execute(old_result_stmt)).scalar_one_or_none()
        if old_result:
            old_issues = (
                await session.execute(
                    select(QcIssueModel).where(
                        QcIssueModel.result_id == old_result.id,
                        QcIssueModel.is_deleted == False,  # noqa: E712
                    )
                )
            ).scalars().all()
            for old_issue in old_issues:
                old_issue.is_deleted = True
                old_issue.deleted_time = datetime.now()
            old_result.is_deleted = True
            old_result.deleted_time = datetime.now()

        staff_quality = result_json.get("staff_quality") or {}
        customer_intent = result_json.get("customer_intent_detail") or {}
        score = staff_quality.get("score", result_json.get("score", 0))
        result_level = staff_quality.get("level", result_json.get("result_level", "pass"))
        risk_level = staff_quality.get("risk_level", result_json.get("risk_level", "none"))
        dimension_scores = staff_quality.get("dimension_scores", result_json.get("dimension_scores"))

        qc_result = QcResultModel(
            result_id=result_id,
            task_id=task.id,
            conversation_id=task.conversation_id,
            score=score,
            result_level=result_level,
            risk_level=risk_level,
            summary=result_json.get("summary"),
            dimension_scores=dimension_scores,
            confidence=result_json.get("confidence"),
            tenant_id=self.auth.tenant_id if self.auth else None,
            created_id=self.auth.user.id if self.auth and self.auth.user else None,
        )
        session.add(qc_result)
        await session.flush()

        for issue_data in result_json.get("issues", []):
            issue_id = f"{result_id}_{issue_data['rule_code']}"

            qc_issue = QcIssueModel(
                issue_id=issue_id,
                result_id=qc_result.id,
                rule_code=issue_data.get("rule_code"),
                severity=issue_data.get("severity"),
                title=issue_data.get("title"),
                reason=issue_data.get("reason"),
                suggested_action=issue_data.get("suggested_action"),
                suggested_reply=issue_data.get("suggested_reply"),
                deduction_score=issue_data.get("deduction_score", 0),
                tenant_id=self.auth.tenant_id if self.auth else None,
                created_id=self.auth.user.id if self.auth and self.auth.user else None,
            )
            session.add(qc_issue)
            await session.flush()

            evidence_message_ids = issue_data.get("evidence_message_ids", [])
            for msg_id in evidence_message_ids:
                msg_stmt = select(DwdQnMessageModel).where(
                    DwdQnMessageModel.message_id == msg_id,
                    DwdQnMessageModel.is_deleted == False,  # noqa: E712
                )
                msg_result = await session.execute(msg_stmt)
                msg = msg_result.scalar_one_or_none()

                if msg:
                    evidence_id = f"{issue_id}_{msg_id}"
                    evidence = QcIssueEvidenceModel(
                        evidence_id=evidence_id,
                        issue_id=qc_issue.id,
                        message_id=msg.id,
                        evidence_text=msg.content_text,
                        tenant_id=self.auth.tenant_id if self.auth else None,
                        created_id=self.auth.user.id if self.auth and self.auth.user else None,
                    )
                    session.add(evidence)

        conv_stmt = select(DwdQnConversationModel).where(DwdQnConversationModel.id == task.conversation_id)
        conv_result = await session.execute(conv_stmt)
        conv = conv_result.scalar_one_or_none()
        if conv:
            conv.qc_status = "completed"

    def _short_hash(self, text: str) -> str:
        """生成短哈希。"""
        return hashlib.sha256(text.encode()).hexdigest()[:8]
