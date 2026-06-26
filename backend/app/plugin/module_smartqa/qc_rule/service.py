"""质检规则管理服务。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_smartqa.models.qc import QcPromptTemplateModel, QcRuleModel, QcRuleVersionModel

from .schema import (
    QcPromptTemplateCreateSchema,
    QcPromptTemplateUpdateSchema,
    QcRuleCreateSchema,
    QcRuleUpdateSchema,
    QcRuleVersionPublishSchema,
)


class QcRuleService:
    """质检规则管理服务。"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def create_rule(self, session: AsyncSession, data: QcRuleCreateSchema) -> QcRuleModel:
        """创建质检规则。"""
        existing_stmt = select(QcRuleModel).where(
            QcRuleModel.rule_code == data.rule_code,
            QcRuleModel.is_deleted == False,  # noqa: E712
        )
        existing = await session.execute(existing_stmt)
        if existing.scalar_one_or_none():
            raise CustomException("规则编码已存在")

        rule = QcRuleModel(
            rule_code=data.rule_code,
            rule_name=data.rule_name,
            category=data.category,
            judgment_standard=data.judgment_standard,
            deduction_score=data.deduction_score,
            severity=data.severity,
            status=data.status,
            tenant_id=self.auth.tenant_id,
            created_id=self.auth.user_id,
        )
        session.add(rule)
        await session.flush()
        await session.refresh(rule)
        return rule

    async def update_rule(self, session: AsyncSession, rule_id: int, data: QcRuleUpdateSchema) -> QcRuleModel:
        """更新质检规则。"""
        stmt = select(QcRuleModel).where(
            QcRuleModel.id == rule_id,
            QcRuleModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise CustomException("规则不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)

        rule.updated_id = self.auth.user_id
        rule.updated_time = datetime.now()
        await session.flush()
        await session.refresh(rule)
        return rule

    async def get_rule(self, session: AsyncSession, rule_id: int) -> QcRuleModel:
        """获取规则详情。"""
        stmt = select(QcRuleModel).where(
            QcRuleModel.id == rule_id,
            QcRuleModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise CustomException("规则不存在")
        return rule

    async def list_rules(self, session: AsyncSession, category: str | None = None, status: str | None = None) -> list[QcRuleModel]:
        """获取规则列表。"""
        stmt = select(QcRuleModel).where(QcRuleModel.is_deleted == False)  # noqa: E712
        if category:
            stmt = stmt.where(QcRuleModel.category == category)
        if status:
            stmt = stmt.where(QcRuleModel.status == status)
        stmt = stmt.order_by(QcRuleModel.category, QcRuleModel.rule_code)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_rule(self, session: AsyncSession, rule_id: int) -> None:
        """删除规则（软删除）。"""
        stmt = select(QcRuleModel).where(
            QcRuleModel.id == rule_id,
            QcRuleModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise CustomException("规则不存在")

        rule.is_deleted = True
        rule.deleted_id = self.auth.user_id
        rule.deleted_time = datetime.now()
        await session.flush()

    async def create_prompt_template(self, session: AsyncSession, data: QcPromptTemplateCreateSchema) -> QcPromptTemplateModel:
        """创建Prompt模板。"""
        existing_stmt = select(QcPromptTemplateModel).where(
            QcPromptTemplateModel.prompt_version == data.prompt_version,
            QcPromptTemplateModel.is_deleted == False,  # noqa: E712
        )
        existing = await session.execute(existing_stmt)
        if existing.scalar_one_or_none():
            raise CustomException("Prompt版本已存在")

        template = QcPromptTemplateModel(
            prompt_version=data.prompt_version,
            name=data.name,
            template_content=data.template_content,
            output_schema_version=data.output_schema_version,
            status=data.status,
            tenant_id=self.auth.tenant_id,
            created_id=self.auth.user_id,
        )
        session.add(template)
        await session.flush()
        await session.refresh(template)
        return template

    async def update_prompt_template(self, session: AsyncSession, template_id: int, data: QcPromptTemplateUpdateSchema) -> QcPromptTemplateModel:
        """更新Prompt模板。"""
        stmt = select(QcPromptTemplateModel).where(
            QcPromptTemplateModel.id == template_id,
            QcPromptTemplateModel.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        if not template:
            raise CustomException("Prompt模板不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        template.updated_id = self.auth.user_id
        template.updated_time = datetime.now()
        await session.flush()
        await session.refresh(template)
        return template

    async def list_prompt_templates(self, session: AsyncSession, status: str | None = None) -> list[QcPromptTemplateModel]:
        """获取Prompt模板列表。"""
        stmt = select(QcPromptTemplateModel).where(QcPromptTemplateModel.is_deleted == False)  # noqa: E712
        if status:
            stmt = stmt.where(QcPromptTemplateModel.status == status)
        stmt = stmt.order_by(QcPromptTemplateModel.created_time.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def publish_rule_version(self, session: AsyncSession, data: QcRuleVersionPublishSchema) -> QcRuleVersionModel:
        """发布规则版本快照。"""
        existing_stmt = select(QcRuleVersionModel).where(
            QcRuleVersionModel.rule_version == data.rule_version,
            QcRuleVersionModel.is_deleted == False,  # noqa: E712
        )
        existing = await session.execute(existing_stmt)
        if existing.scalar_one_or_none():
            raise CustomException("规则版本已存在")

        prompt_stmt = select(QcPromptTemplateModel).where(
            QcPromptTemplateModel.prompt_version == data.prompt_version,
            QcPromptTemplateModel.is_deleted == False,  # noqa: E712
        )
        prompt_result = await session.execute(prompt_stmt)
        if not prompt_result.scalar_one_or_none():
            raise CustomException("Prompt版本不存在")

        rules_stmt = select(QcRuleModel).where(
            QcRuleModel.rule_code.in_(data.rule_codes),
            QcRuleModel.is_deleted == False,  # noqa: E712
        )
        rules_result = await session.execute(rules_stmt)
        rules = list(rules_result.scalars().all())

        if len(rules) != len(data.rule_codes):
            raise CustomException("部分规则编码不存在")

        rule_snapshot = {
            rule.rule_code: {
                "rule_name": rule.rule_name,
                "category": rule.category,
                "judgment_standard": rule.judgment_standard,
                "deduction_score": rule.deduction_score,
                "severity": rule.severity,
            }
            for rule in rules
        }

        version = QcRuleVersionModel(
            rule_version=data.rule_version,
            prompt_version=data.prompt_version,
            rule_codes=data.rule_codes,
            rule_snapshot=rule_snapshot,
            status="active",
            published_at=datetime.now(),
            tenant_id=self.auth.tenant_id,
            created_id=self.auth.user_id,
        )
        session.add(version)
        await session.flush()
        await session.refresh(version)
        return version

    async def list_rule_versions(self, session: AsyncSession, status: str | None = None) -> list[QcRuleVersionModel]:
        """获取规则版本列表。"""
        stmt = select(QcRuleVersionModel).where(QcRuleVersionModel.is_deleted == False)  # noqa: E712
        if status:
            stmt = stmt.where(QcRuleVersionModel.status == status)
        stmt = stmt.order_by(QcRuleVersionModel.published_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())
