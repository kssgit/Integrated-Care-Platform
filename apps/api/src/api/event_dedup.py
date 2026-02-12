from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
import time
from typing import Protocol


class ProcessedEventStore(ABC):
    @abstractmethod
    async def mark_once(self, event_id: str, ttl_seconds: int) -> bool:
        raise NotImplementedError


class RedisLikeDedupClient(Protocol):
    async def set(self, key: str, value: str, ex: int, nx: bool) -> bool | None: ...


class InMemoryProcessedEventStore(ProcessedEventStore):
    def __init__(self) -> None:
        self._expires_at: dict[str, float] = defaultdict(float)

    async def mark_once(self, event_id: str, ttl_seconds: int) -> bool:
        now = time.time()
        expires = self._expires_at.get(event_id, 0.0)
        if expires > now:
            return False
        self._expires_at[event_id] = now + ttl_seconds
        return True


class RedisProcessedEventStore(ProcessedEventStore):
    def __init__(self, client: RedisLikeDedupClient) -> None:
        self._client = client

    async def mark_once(self, event_id: str, ttl_seconds: int) -> bool:
        key = f"api_event_dedup:{event_id}"
        created = await self._client.set(key, "1", ex=ttl_seconds, nx=True)
        return bool(created)

