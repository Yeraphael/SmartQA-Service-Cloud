from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate_query(
    db: AsyncSession,
    stmt: Select,
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    """Execute a SQLAlchemy select with simple pagination."""

    page_no = max(page_no, 1)
    page_size = max(min(page_size, 100), 1)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.offset((page_no - 1) * page_size).limit(page_size))
    rows = result.mappings().all()
    return {
        "page_no": page_no,
        "page_size": page_size,
        "total": total,
        "has_next": page_no * page_size < total,
        "items": [dict(row) for row in rows],
    }

