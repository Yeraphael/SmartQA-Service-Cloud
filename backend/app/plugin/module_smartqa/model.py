"""Aggregate SmartQA models for Alembic and framework model discovery."""

from app.plugin.module_smartqa.models.conversation import DwdCustomerStaffRelationModel, DwdQnConversationModel, DwdQnMessageModel
from app.plugin.module_smartqa.models.dimension import DimCustomerIdentityModel, DimCustomerModel, DimProductModel, DimShopModel, DimStaffAccountModel, DimStaffModel
from app.plugin.module_smartqa.models.ods import OdsImportBatchModel, OdsQnChatRecordModel, OdsQnShopRecordModel
from app.plugin.module_smartqa.models.qc import ModelCallLogModel, QcIssueEvidenceModel, QcIssueModel, QcPromptTemplateModel, QcResultModel, QcRuleModel, QcRuleVersionModel, QcTaskModel

__all__ = [
    "DwdCustomerStaffRelationModel",
    "DwdQnConversationModel",
    "DwdQnMessageModel",
    "DimCustomerIdentityModel",
    "DimCustomerModel",
    "DimProductModel",
    "DimShopModel",
    "DimStaffAccountModel",
    "DimStaffModel",
    "ModelCallLogModel",
    "OdsImportBatchModel",
    "OdsQnChatRecordModel",
    "OdsQnShopRecordModel",
    "QcIssueEvidenceModel",
    "QcIssueModel",
    "QcPromptTemplateModel",
    "QcResultModel",
    "QcRuleModel",
    "QcRuleVersionModel",
    "QcTaskModel",
]

