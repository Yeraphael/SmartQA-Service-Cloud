"""Sync source database (aizhijian) into SmartQA ODS/DWD."""

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.pipeline import SmartQAPipeline, get_source_config


class SourceDbSyncService:
    """Source database sync service used by HTTP APIs and scripts."""

    def __init__(self, source_config: dict | None = None, auth: AuthSchema | None = None):
        self.source_config = source_config or get_source_config()
        self.auth = auth

    async def full_sync(self, session=None, build: bool = True, seed: bool = True, truncate_dwd: bool = False) -> dict:
        pipeline = SmartQAPipeline(
            source_config=self.source_config,
            tenant_id=self.auth.tenant_id if self.auth else 1,
            created_id=self.auth.user_id if self.auth else None,
        )
        sync_result = pipeline.full_sync()
        build_result = pipeline.rebuild_warehouse(sync_result["batch_id"], truncate_dwd=truncate_dwd) if build else {}
        seed_result = pipeline.seed_defaults() if seed else {}
        return {
            **sync_result,
            "build_result": build_result,
            "seed_result": seed_result,
        }
