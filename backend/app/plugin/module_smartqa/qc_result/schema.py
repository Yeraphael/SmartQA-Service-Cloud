from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.base_params import QueryParam
from app.core.validator import DateTimeStr


@dataclass
class QcResultQueryParam(QueryParam):
    keyword: str | None = Query(None, description="客户/客服/商品关键词")
    staff_id: int | None = Query(None, description="客服ID")
    shop_id: int | None = Query(None, description="店铺ID")
    result_level: str | None = Query(None, description="结果等级")
    risk_level: str | None = Query(None, description="风险等级")
    start_time: DateTimeStr | None = Query(None, description="开始时间")
    end_time: DateTimeStr | None = Query(None, description="结束时间")


class QcResultDetailSchema(BaseModel):
    result: dict = Field(default_factory=dict, description="质检结果")
    issues: list[dict] = Field(default_factory=list, description="问题列表")
    evidences: list[dict] = Field(default_factory=list, description="证据列表")

