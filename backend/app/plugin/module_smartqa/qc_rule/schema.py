"""质检规则相关的Schema定义。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QcRuleCreateSchema(BaseModel):
    """创建质检规则。"""

    rule_code: str = Field(..., description="规则编码", max_length=64)
    rule_name: str = Field(..., description="规则名称", max_length=128)
    category: str = Field(..., description="规则分类", max_length=64)
    judgment_standard: str = Field(..., description="判断标准")
    deduction_score: int = Field(0, description="扣分")
    severity: str = Field("medium", description="严重程度")
    status: str = Field("active", description="状态")


class QcRuleUpdateSchema(BaseModel):
    """更新质检规则。"""

    rule_name: str | None = Field(None, description="规则名称", max_length=128)
    category: str | None = Field(None, description="规则分类", max_length=64)
    judgment_standard: str | None = Field(None, description="判断标准")
    deduction_score: int | None = Field(None, description="扣分")
    severity: str | None = Field(None, description="严重程度")
    status: str | None = Field(None, description="状态")


class QcRuleSchema(BaseModel):
    """质检规则响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_code: str
    rule_name: str
    category: str
    judgment_standard: str
    deduction_score: int
    severity: str
    status: str
    created_time: datetime
    updated_time: datetime


class QcPromptTemplateCreateSchema(BaseModel):
    """创建Prompt模板。"""

    prompt_version: str = Field(..., description="Prompt版本", max_length=64)
    name: str = Field(..., description="模板名称", max_length=128)
    template_content: str = Field(..., description="模板内容")
    output_schema_version: str = Field(..., description="输出结构版本", max_length=64)
    status: str = Field("active", description="状态")


class QcPromptTemplateUpdateSchema(BaseModel):
    """更新Prompt模板。"""

    name: str | None = Field(None, description="模板名称", max_length=128)
    template_content: str | None = Field(None, description="模板内容")
    output_schema_version: str | None = Field(None, description="输出结构版本")
    status: str | None = Field(None, description="状态")


class QcPromptTemplateSchema(BaseModel):
    """Prompt模板响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_version: str
    name: str
    template_content: str
    output_schema_version: str
    status: str
    created_time: datetime
    updated_time: datetime


class QcRuleVersionPublishSchema(BaseModel):
    """发布规则版本。"""

    rule_version: str = Field(..., description="规则版本名称", max_length=64)
    prompt_version: str = Field(..., description="使用的Prompt版本", max_length=64)
    rule_codes: list[str] = Field(..., description="包含的规则编码列表")


class QcRuleVersionSchema(BaseModel):
    """规则版本响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_version: str
    prompt_version: str
    rule_codes: list[str] | None
    rule_snapshot: dict | None
    status: str
    published_at: datetime | None
    created_time: datetime
    updated_time: datetime
