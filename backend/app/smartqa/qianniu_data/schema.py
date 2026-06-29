from dataclasses import dataclass

from fastapi import Query

from app.core.base_params import QueryParam


@dataclass
class ImportBatchQueryParam(QueryParam):
    status: str | None = Query(None, description="批次状态")
    source_type: str | None = Query(None, description="来源类型")
