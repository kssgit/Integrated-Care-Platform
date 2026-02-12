from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque


class RateLimitStore(ABC):
    @abstractmethod
    async def add_request(self, key: str, now_seconds: float) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_since(self, key: str, cutoff_seconds: float) -> int:
        raise NotImplementedError


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

