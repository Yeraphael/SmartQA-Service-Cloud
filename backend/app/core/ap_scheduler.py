"""SmartQA product scheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.asyncio.client import Redis

from app.config.setting import settings
from app.core.logger import logger
from app.plugin.module_smartqa.pipeline import SmartQAPipeline


class SchedulerUtil:
    """Run only SmartQA source sync and daily QC jobs."""

    redis_instance: Redis | None = None
    _scheduler: AsyncIOScheduler | None = None
    _running: bool = False
    _sync_lock: asyncio.Lock | None = None
    _qc_lock: asyncio.Lock | None = None

    @classmethod
    async def init_scheduler(cls, redis: Redis) -> None:
        cls.redis_instance = redis
        cls._sync_lock = asyncio.Lock()
        cls._qc_lock = asyncio.Lock()
        if cls._scheduler and cls._scheduler.running:
            cls._running = True
            return

        timezone = ZoneInfo(settings.SMARTQA_SCHEDULER_TIMEZONE)
        scheduler = AsyncIOScheduler(timezone=timezone)
        cls._scheduler = scheduler

        for hour, minute in cls._parse_times(settings.SMARTQA_SOURCE_SYNC_TIMES):
            scheduler.add_job(
                cls.run_source_sync,
                CronTrigger(hour=hour, minute=minute, timezone=timezone),
                id=f"smartqa_source_sync_{hour:02d}{minute:02d}",
                name=f"SmartQA source sync {hour:02d}:{minute:02d}",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=3600,
            )

        qc_hour, qc_minute = cls._parse_single_time(settings.SMARTQA_DAILY_QC_TIME)
        scheduler.add_job(
            cls.run_daily_qc_sample,
            CronTrigger(hour=qc_hour, minute=qc_minute, timezone=timezone),
            id="smartqa_daily_qc_sample",
            name=f"SmartQA daily QC sample {qc_hour:02d}:{qc_minute:02d}",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=7200,
        )

        scheduler.start()
        cls._running = True
        logger.info("SmartQA scheduler started with jobs: {}", cls.get_jobs())

    @classmethod
    async def shutdown(cls, wait: bool = True) -> None:
        if cls._scheduler:
            cls._scheduler.shutdown(wait=wait)
            cls._scheduler = None
        cls._running = False
        cls.redis_instance = None

    @classmethod
    def is_running(cls) -> bool:
        return bool(cls._scheduler and cls._scheduler.running and cls._running)

    @classmethod
    def get_jobs(cls) -> list[dict[str, str | None]]:
        if not cls._scheduler:
            return []
        jobs = []
        for job in cls._scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            jobs.append({"id": job.id, "name": job.name, "next_run_time": next_run})
        return jobs

    @classmethod
    async def run_source_sync(cls) -> dict:
        lock = cls._sync_lock or asyncio.Lock()
        cls._sync_lock = lock
        if lock.locked():
            logger.warning("SmartQA source sync skipped because previous sync is still running")
            return {"skipped": True, "reason": "previous sync is still running"}
        async with lock:
            started = datetime.now()
            logger.info("SmartQA scheduled source sync started at {}", started)
            result = await asyncio.to_thread(cls._source_sync_pipeline)
            logger.info("SmartQA scheduled source sync finished: {}", result)
            return result

    @classmethod
    async def run_daily_qc_sample(cls) -> dict:
        lock = cls._qc_lock or asyncio.Lock()
        cls._qc_lock = lock
        if lock.locked():
            logger.warning("SmartQA daily QC skipped because previous QC job is still running")
            return {"skipped": True, "reason": "previous QC job is still running"}
        async with lock:
            logger.info("SmartQA daily QC sample started")
            result = await asyncio.to_thread(
                SmartQAPipeline().run_daily_qc_sample,
                limit=settings.SMARTQA_DAILY_QC_SAMPLE_LIMIT,
                execute=settings.SMARTQA_DAILY_QC_EXECUTE,
            )
            logger.info("SmartQA daily QC sample finished: {}", result)
            return result

    @staticmethod
    def _source_sync_pipeline() -> dict:
        pipeline = SmartQAPipeline()
        sync_result = pipeline.full_sync()
        build_result = pipeline.rebuild_warehouse(sync_result["batch_id"], truncate_dwd=False)
        seed_result = pipeline.seed_defaults()
        return {"sync": sync_result, "build": build_result, "seed": seed_result}

    @staticmethod
    def _parse_times(raw: str) -> list[tuple[int, int]]:
        times: list[tuple[int, int]] = []
        for item in (raw or "").split(","):
            item = item.strip()
            if not item:
                continue
            times.append(SchedulerUtil._parse_single_time(item))
        return times or [(7, 30), (12, 30), (20, 30)]

    @staticmethod
    def _parse_single_time(raw: str) -> tuple[int, int]:
        try:
            hour_raw, minute_raw = raw.strip().split(":", 1)
            hour = int(hour_raw)
            minute = int(minute_raw)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return hour, minute
        except ValueError:
            logger.warning("Invalid SmartQA schedule time '{}', fallback to 23:00", raw)
            return 23, 0
