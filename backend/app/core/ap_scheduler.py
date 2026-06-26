"""Minimal scheduler compatibility layer for SmartQA.

P0 SmartQA runs its real data pipeline through explicit API/script commands.
The former template workflow/cron modules were removed, so this class keeps
startup code compatible without registering unrelated background jobs.
"""

from redis.asyncio.client import Redis


class SchedulerUtil:
    """No-op scheduler facade kept for optional startup compatibility."""

    redis_instance: Redis | None = None
    _running: bool = False

    @classmethod
    async def init_scheduler(cls, redis: Redis) -> None:
        cls.redis_instance = redis
        cls._running = False

    @classmethod
    async def shutdown(cls, wait: bool = True) -> None:
        cls._running = False
        cls.redis_instance = None

    @classmethod
    def is_running(cls) -> bool:
        return cls._running
