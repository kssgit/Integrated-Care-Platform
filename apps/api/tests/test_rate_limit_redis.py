from __future__ import annotations

from collections import defaultdict

import pytest

from api.rate_limit import RedisRateLimitStore


class FakeRedis:
    def __init__(self) -> None:
        self._sets: dict[str, dict[str, float]] = defaultdict(dict)

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        before = len(self._sets[key])
        self._sets[key].update(mapping)
        return 1 if len(self._sets[key]) > before else 0

    async def zremrangebyscore(self, key: str, min: float, max: float) -> int:
        members = self._sets[key]
        targets = [member for member, score in members.items() if min <= score <= max]
        for member in targets:
            members.pop(member, None)
        return len(targets)

    async def zcard(self, key: str) -> int:
        return len(self._sets[key])

    async def expire(self, key: str, time: int) -> bool:
        _ = (key, time)
        return True


@pytest.mark.asyncio
async def test_redis_rate_limit_store_counts_with_cutoff() -> None:
    store = RedisRateLimitStore(FakeRedis(), window_seconds=60)
    await store.add_request("client-a", 100.0)
    await store.add_request("client-a", 120.0)
    await store.add_request("client-a", 150.0)

    count = await store.count_since("client-a", cutoff_seconds=120.0)

    assert count == 2

