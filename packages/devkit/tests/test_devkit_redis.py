import pytest

from devkit.redis import AsyncRedisManager, create_redis_client, create_revoked_token_store
from shared.security import InMemoryRevokedTokenStore


def test_create_redis_client_none() -> None:
    assert create_redis_client(None) is None


def test_create_revoked_token_store_fallback() -> None:
    store = create_revoked_token_store(None)
    assert isinstance(store, InMemoryRevokedTokenStore)


@pytest.mark.asyncio
async def test_async_redis_manager_reconnects_on_failure() -> None:
    class FakeClient:
        def __init__(self, fail_once: bool) -> None:
            self.fail_once = fail_once
            self.ping_count = 0

        async def ping(self) -> bool:
            self.ping_count += 1
            return True

        async def incr(self, _key: str) -> int:
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError("transient")
            return 1

        async def close(self) -> None:
            return None

    created: list[FakeClient] = []

    def factory(_url: str) -> FakeClient:
        client = FakeClient(fail_once=(len(created) == 0))
        created.append(client)
        return client

    manager = AsyncRedisManager("redis://example:6379/0", client_factory=factory)
    value = await manager.execute("incr", "k1")
    assert value == 1
    assert len(created) >= 2
