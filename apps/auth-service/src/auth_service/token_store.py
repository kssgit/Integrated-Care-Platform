from __future__ import annotations

import time
from typing import Protocol


class RedisLike(Protocol):
    async def setex(self, key: str, seconds: int, value: str) -> bool: ...

    async def exists(self, key: str) -> int: ...


class RevokedTokenStore:
    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        raise NotImplementedError

    async def is_revoked(self, jti: str) -> bool:
        raise NotImplementedError


class InMemoryRevokedTokenStore(RevokedTokenStore):
    def __init__(self) -> None:
        self._items: dict[str, float] = {}

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self._items[jti] = time.time() + ttl_seconds

    async def is_revoked(self, jti: str) -> bool:
        expiry = self._items.get(jti)
        if expiry is None:
            return False
        if expiry < time.time():
            self._items.pop(jti, None)
            return False
        return True


class RedisRevokedTokenStore(RevokedTokenStore):
    def __init__(self, redis_client: RedisLike) -> None:
        self._redis = redis_client

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.setex(f"auth:revoked:{jti}", ttl_seconds, "1")

    async def is_revoked(self, jti: str) -> bool:
        return (await self._redis.exists(f"auth:revoked:{jti}")) > 0

