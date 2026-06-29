from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class SmartQABulkModelMixin(MappedBase):
    """Lean base for SmartQA ODS/DIM/DWD bulk tables."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已删除", index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间", index=True)
    updated_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间", index=True)
    deleted_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="删除时间", index=True)
