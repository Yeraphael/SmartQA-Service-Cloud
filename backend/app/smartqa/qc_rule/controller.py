"""质检规则管理控制器。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.smartqa.common.access import ensure_smartqa_boss

from .schema import (
    QcPromptTemplateCreateSchema,
    QcPromptTemplateSchema,
    QcPromptTemplateUpdateSchema,
    QcRuleCreateSchema,
    QcRuleSchema,
    QcRuleUpdateSchema,
    QcRuleVersionPublishSchema,
    QcRuleVersionSchema,
)
from .service import QcRuleService

router = APIRouter(prefix="/qc/rules", tags=["SmartQA - 质检规则"])


@router.get("", summary="获取规则列表", response_model=ResponseSchema[list[QcRuleSchema]])
async def list_rules(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    category: str | None = Query(None, description="规则分类"),
    status: str | None = Query(None, description="状态"),
):
    await ensure_smartqa_boss(auth)
    rules = await QcRuleService(auth).list_rules(session, category, status)
    return SuccessResponse(data=[QcRuleSchema.model_validate(rule) for rule in rules], msg="查询成功")


@router.post("", summary="创建质检规则", response_model=ResponseSchema[QcRuleSchema])
async def create_rule(
    data: QcRuleCreateSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    rule = await QcRuleService(auth).create_rule(session, data)
    await session.commit()
    return SuccessResponse(data=QcRuleSchema.model_validate(rule), msg="创建成功")


@router.get("/prompt-templates", summary="获取Prompt模板列表", response_model=ResponseSchema[list[QcPromptTemplateSchema]])
async def list_prompt_templates(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    status: str | None = Query(None, description="状态"),
):
    await ensure_smartqa_boss(auth)
    templates = await QcRuleService(auth).list_prompt_templates(session, status)
    return SuccessResponse(data=[QcPromptTemplateSchema.model_validate(t) for t in templates], msg="查询成功")


@router.post("/prompt-templates", summary="创建Prompt模板", response_model=ResponseSchema[QcPromptTemplateSchema])
async def create_prompt_template(
    data: QcPromptTemplateCreateSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    template = await QcRuleService(auth).create_prompt_template(session, data)
    await session.commit()
    return SuccessResponse(data=QcPromptTemplateSchema.model_validate(template), msg="创建成功")


@router.put("/prompt-templates/{template_id}", summary="更新Prompt模板", response_model=ResponseSchema[QcPromptTemplateSchema])
async def update_prompt_template(
    template_id: int,
    data: QcPromptTemplateUpdateSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    template = await QcRuleService(auth).update_prompt_template(session, template_id, data)
    await session.commit()
    return SuccessResponse(data=QcPromptTemplateSchema.model_validate(template), msg="更新成功")


@router.get("/versions", summary="获取规则版本列表", response_model=ResponseSchema[list[QcRuleVersionSchema]])
async def list_rule_versions(
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
    status: str | None = Query(None, description="状态"),
):
    await ensure_smartqa_boss(auth)
    versions = await QcRuleService(auth).list_rule_versions(session, status)
    return SuccessResponse(data=[QcRuleVersionSchema.model_validate(v) for v in versions], msg="查询成功")


@router.post("/versions/publish", summary="发布规则版本", response_model=ResponseSchema[QcRuleVersionSchema])
async def publish_rule_version(
    data: QcRuleVersionPublishSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    version = await QcRuleService(auth).publish_rule_version(session, data)
    await session.commit()
    return SuccessResponse(data=QcRuleVersionSchema.model_validate(version), msg="发布成功")


@router.get("/{rule_id}", summary="获取规则详情", response_model=ResponseSchema[QcRuleSchema])
async def get_rule(
    rule_id: int,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    rule = await QcRuleService(auth).get_rule(session, rule_id)
    return SuccessResponse(data=QcRuleSchema.model_validate(rule), msg="查询成功")


@router.put("/{rule_id}", summary="更新质检规则", response_model=ResponseSchema[QcRuleSchema])
async def update_rule(
    rule_id: int,
    data: QcRuleUpdateSchema,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    rule = await QcRuleService(auth).update_rule(session, rule_id, data)
    await session.commit()
    return SuccessResponse(data=QcRuleSchema.model_validate(rule), msg="更新成功")


@router.delete("/{rule_id}", summary="删除规则", response_model=ResponseSchema[dict])
async def delete_rule(
    rule_id: int,
    session: Annotated[AsyncSession, Depends(db_getter)],
    auth: AuthSchema = Depends(AuthPermission()),
):
    await ensure_smartqa_boss(auth)
    await QcRuleService(auth).delete_rule(session, rule_id)
    await session.commit()
    return SuccessResponse(data={"message": "删除成功"}, msg="删除成功")
