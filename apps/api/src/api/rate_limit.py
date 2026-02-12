from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Protocol
from uuid import uuid4


class RateLimitStore(ABC):
    @abstractmethod
    async def add_request(self, key: str, now_seconds: float) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_since(self, key: str, cutoff_seconds: float) -> int:
        raise NotImplementedError


class RedisLikeClient(Protocol):
    async def zadd(self, key: str, mapping: dict[str, float]) -> int: ...

    async def zremrangebyscore(self, key: str, min: float, max: float) -> int: ...

    async def zcard(self, key: str) -> int: ...

    async def expire(self, key: str, time: int) -> bool: ...


class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def add_request(self, key: str, now_seconds: float) -> None:
        self._requests[key].append(now_seconds)

    async def count_since(self, key: str, cutoff_seconds: float) -> int:
        queue = self._requests[key]
        while queue and queue[0] < cutoff_seconds:
            queue.popleft()
        return len(queue)


class RedisRateLimitStore(RateLimitStore):
    def __init__(self, client: RedisLikeClient, window_seconds: int = 60) -> None:
        self._client = client
        self._window_seconds = window_seconds

    async def add_request(self, key: str, now_seconds: float) -> None:
        redis_key = self._redis_key(key)
        member = f"{now_seconds:.6f}:{uuid4()}"
        await self._client.zadd(redis_key, {member: now_seconds})
        await self._client.expire(redis_key, self._window_seconds + 5)

    async def count_since(self, key: str, cutoff_seconds: float) -> int:
        redis_key = self._redis_key(key)
        await self._client.zremrangebyscore(redis_key, float("-inf"), cutoff_seconds - 1e-9)
        return await self._client.zcard(redis_key)

    def _redis_key(self, key: str) -> str:
        return f"rate_limit:{key}"


class SlidingWindowRateLimiter:
    def __init__(
        self,
        store: RateLimitStore,
        limit_per_minute: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self._store = store
        self._limit = limit_per_minute
        self._window_seconds = window_seconds

    async def allow(self, key: str, now_seconds: float) -> bool:
        cutoff = now_seconds - self._window_seconds
        request_count = await self._store.count_since(key, cutoff)
        if request_count >= self._limit:
            return False
        await self._store.add_request(key, now_seconds)
        return True
