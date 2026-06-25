from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.base_params import QueryParam
from app.core.validator import DateTimeStr


@dataclass
class ConversationQueryParam(QueryParam):
    keyword: str | None = Query(None, description="客户/客服/商品关键词")
    shop_id: int | None = Query(None, description="店铺ID")
    staff_id: int | None = Query(None, description="客服ID")
    customer_id: int | None = Query(None, description="客户ID")
    qn_status: str | None = Query(None, description="千牛状态")
    qc_status: str | None = Query(None, description="质检状态")
    start_time: DateTimeStr | None = Query(None, description="开始时间")
    end_time: DateTimeStr | None = Query(None, description="结束时间")


class ConversationDetailSchema(BaseModel):
    conversation: dict = Field(default_factory=dict, description="会话信息")
    messages: list[dict] = Field(default_factory=list, description="消息列表")

