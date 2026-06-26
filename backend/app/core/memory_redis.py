"""Small Redis-compatible store for local Redis-disabled deployments."""

from __future__ import annotations

import fnmatch
import time
from typing import Any


class MemoryRedis:
    """Async subset used by auth, cache and middleware when Redis is disabled."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}

    def _purge(self, key: str) -> None:
        item = self._data.get(key)
        if item and item[1] is not None and item[1] <= time.time():
            self._data.pop(key, None)

    def _deadline(self, ex: int | None = None) -> float | None:
        return time.time() + ex if ex else None

    @staticmethod
    def _string(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def get(self, key: str) -> str | None:
        self._purge(key)
        item = self._data.get(key)
        return item[0] if item else None

    async def set(self, name: str, value: Any, ex: int | None = None, nx: bool = False) -> bool | None:
        self._purge(name)
        if nx and name in self._data:
            return None
        self._data[name] = (self._string(value), self._deadline(ex))
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._data:
                count += 1
                self._data.pop(key, None)
        return count

    async def exists(self, key: str) -> int:
        self._purge(key)
        return 1 if key in self._data else 0

    async def ttl(self, key: str) -> int:
        self._purge(key)
        item = self._data.get(key)
        if not item:
            return -2
        if item[1] is None:
            return -1
        return max(int(item[1] - time.time()), -2)

    async def expire(self, key: str, expire: int) -> bool:
        self._purge(key)
        item = self._data.get(key)
        if not item:
            return False
        self._data[key] = (item[0], self._deadline(expire))
        return True

    async def keys(self, pattern: str = "*") -> list[str]:
        for key in list(self._data):
            self._purge(key)
        return [key for key in self._data if fnmatch.fnmatch(key, pattern)]

    async def mget(self, *keys: str) -> list[str | None]:
        return [await self.get(key) for key in keys]

    async def scan_iter(self, match: str = "*"):
        for key in await self.keys(match):
            yield key

    async def eval(self, script: str, numkeys: int, key: str, *args: str) -> int:
        # Only lock release/renew scripts in RedisCURD use eval.
        current = await self.get(key)
        if current is None or not args or current != args[0]:
            return 0
        if "expire" in script.lower() and len(args) > 1:
            return 1 if await self.expire(key, int(args[1])) else 0
        return await self.delete(key)

    async def info(self) -> dict[str, Any]:
        return {"redis_version": "memory", "used_memory_human": f"{len(self._data)} keys"}

    async def dbsize(self) -> int:
        for key in list(self._data):
            self._purge(key)
        return len(self._data)

    async def close(self) -> None:
        self._data.clear()
