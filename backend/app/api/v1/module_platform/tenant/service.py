"""Single-tenant configuration service used by authentication startup."""

import json

from redis.asyncio.client import Redis
from sqlalchemy import select

from app.common.enums import RedisInitKeyConfig
from app.core.base_schema import AuthSchema
from app.core.redis_crud import RedisCURD

from .model import TenantModel


class TenantService:
    """SmartQA keeps tenant data only as login context and site branding."""

    def __init__(self, auth: AuthSchema | None = None) -> None:
        self.auth = auth

    @staticmethod
    async def init_cache(redis: Redis) -> None:
        """Cache active tenant basics for middleware/header configuration."""

        from app.core.database import async_db_session

        async with async_db_session() as session:
            result = await session.execute(
                select(TenantModel).where(
                    TenantModel.status == 0,
                    TenantModel.is_deleted == False,  # noqa: E712
                )
            )
            tenants = result.scalars().all()

        payload = {
            str(tenant.id): {
                "id": tenant.id,
                "name": tenant.name,
                "code": tenant.code,
                "logo_url": tenant.logo_url,
                "favicon": tenant.favicon,
                "login_bg": tenant.login_bg,
                "copyright": tenant.copyright,
            }
            for tenant in tenants
        }
        await RedisCURD(redis).set(
            key=RedisInitKeyConfig.TENANT_CONFIG.key,
            value=json.dumps(payload, ensure_ascii=False),
        )

    async def check_quota(self, tenant_id: int | None, resource_type: str) -> None:
        """P0 has no package quotas; this method is kept for compatibility."""

        return None
