"""Aggregate SmartQA models for Alembic metadata discovery."""

from app.smartqa.models.conversation import DwdCustomerStaffRelationModel, DwdQnConversationModel, DwdQnMessageModel
from app.smartqa.models.dimension import DimCustomerIdentityModel, DimCustomerModel, DimProductModel, DimShopModel, DimStaffAccountModel, DimStaffModel
from app.smartqa.models.ods import OdsImportBatchModel, OdsQnChatRecordModel, OdsQnShopRecordModel
from app.smartqa.models.qc import ModelCallLogModel, QcIssueEvidenceModel, QcIssueModel, QcPromptTemplateModel, QcResultModel, QcRuleModel, QcRuleVersionModel, QcTaskModel

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
