import pytest

from api.rate_limit import InMemoryRateLimitStore, SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit() -> None:
    limiter = SlidingWindowRateLimiter(InMemoryRateLimitStore(), limit_per_minute=2, window_seconds=60)
    now = 1000.0

    assert await limiter.allow("client-a", now) is True
    assert await limiter.allow("client-a", now + 1) is True
    assert await limiter.allow("client-a", now + 2) is False


@pytest.mark.asyncio
async def test_rate_limiter_allows_new_window() -> None:
    limiter = SlidingWindowRateLimiter(InMemoryRateLimitStore(), limit_per_minute=1, window_seconds=60)
    now = 1000.0

    assert await limiter.allow("client-a", now) is True
    assert await limiter.allow("client-a", now + 61) is True

