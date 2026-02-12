from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol


class CacheStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError


class RedisLikeCacheClient(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def setex(self, key: str, seconds: int, value: str) -> bool: ...


class InMemoryCacheStore(CacheStore):
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}

    async def get(self, key: str) -> dict[str, Any] | None:
        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= time.time():
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._items[key] = (time.time() + ttl_seconds, value)


class RedisCacheStore(CacheStore):
    def __init__(self, client: RedisLikeCacheClient) -> None:
        self._client = client

    async def get(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        payload = json.dumps(value, ensure_ascii=True)
        await self._client.setex(key, ttl_seconds, payload)


@dataclass
class FacilityCache:
    store: CacheStore
    ttl_seconds: int = 30

    async def get(self, key: str) -> dict[str, Any] | None:
        return await self.store.get(key)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        await self.store.set(key, value, self.ttl_seconds)
