import pytest

from data_pipeline.core.exceptions import ProviderRequestError
from data_pipeline.core.retry import with_exponential_backoff


@pytest.mark.asyncio
async def test_backoff_retries_until_success() -> None:
    state = {"count": 0}

    async def flaky_operation() -> str:
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    result = await with_exponential_backoff(flaky_operation, retries=3, base_delay_seconds=0.0)
    assert result == "ok"
    assert state["count"] == 3


@pytest.mark.asyncio
async def test_backoff_raises_after_max_retry() -> None:
    async def failing_operation() -> str:
        raise RuntimeError("hard failure")

    with pytest.raises(ProviderRequestError):
        await with_exponential_backoff(failing_operation, retries=3, base_delay_seconds=0.0)
