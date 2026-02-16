import asyncio
from typing import Awaitable, Callable, TypeVar

from data_pipeline.core.exceptions import ProviderRequestError

T = TypeVar("T")


async def with_exponential_backoff(
    operation: Callable[[], Awaitable[T]],
    retries: int = 3,
    base_delay_seconds: float = 0.1,
    on_retry: Callable[[int, float], None] | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
) -> T:
    attempt = 0
    while attempt < retries:
        try:
            return await operation()
        except Exception as exc:
            if should_retry and not should_retry(exc):
                raise ProviderRequestError(str(exc)) from exc
            attempt += 1
            if attempt >= retries:
                raise ProviderRequestError(str(exc)) from exc
            delay = base_delay_seconds * (2 ** (attempt - 1))
            if on_retry:
                on_retry(attempt, delay)
            await asyncio.sleep(delay)
    raise ProviderRequestError("retry attempts exhausted")
