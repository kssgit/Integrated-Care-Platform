from __future__ import annotations

import asyncio
from typing import Any
from collections.abc import Callable

from shared.security import InMemoryRevokedTokenStore, RedisRevokedTokenStore, RevokedTokenStore


class AsyncRedisManager:
    def __init__(
        self,
        url: str,
        *,
        max_retries: int = 3,
        base_delay_seconds: float = 0.2,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._url = url
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._client_factory = client_factory
        self._client: Any | None = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> Any:
        async with self._lock:
            if self._client is None:
                self._client = self._new_client()
            try:
                await self._client.ping()
            except Exception:
                self._client = self._new_client()
                await self._client.ping()
            return self._client

    async def reconnect(self) -> Any:
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.close()
                except Exception:
                    pass
            self._client = self._new_client()
            await self._client.ping()
            return self._client

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.close()
                finally:
                    self._client = None

    async def execute(self, operation: str, *args, **kwargs):
        attempt = 0
        while True:
            client = await self.get_client()
            method = getattr(client, operation)
            try:
                return await method(*args, **kwargs)
            except Exception:
                attempt += 1
                if attempt >= self._max_retries:
                    raise
                await self.reconnect()
                await asyncio.sleep(self._base_delay_seconds * (2 ** (attempt - 1)))

    def _new_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(self._url)
        import redis.asyncio as redis

        return redis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )

    def __getattr__(self, name: str):
        async def _call(*args, **kwargs):
            return await self.execute(name, *args, **kwargs)

        return _call


def create_redis_client(url: str | None):
    if not url:
        return None
    try:
        return AsyncRedisManager(url)
    except Exception:
        return None


def create_revoked_token_store(redis_client: Any | None) -> RevokedTokenStore:
    if redis_client is None:
        return InMemoryRevokedTokenStore()
    return RedisRevokedTokenStore(redis_client)


def create_rate_limit_store(redis_client: Any | None, window_seconds: int = 60):
    from api.rate_limit import InMemoryRateLimitStore, RedisRateLimitStore

    if redis_client is None:
        return InMemoryRateLimitStore()
    return RedisRateLimitStore(redis_client, window_seconds=window_seconds)


def create_dedup_store(redis_client: Any | None):
    from api.event_dedup import InMemoryProcessedEventStore, RedisProcessedEventStore

    if redis_client is None:
        return InMemoryProcessedEventStore()
    return RedisProcessedEventStore(redis_client)
