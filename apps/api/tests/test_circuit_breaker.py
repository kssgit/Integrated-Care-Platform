import pytest

from api.circuit_breaker import CircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=30)
    now = 100.0

    async def fail_call() -> str:
        raise RuntimeError("external failure")

    with pytest.raises(RuntimeError):
        await breaker.call(fail_call, now_seconds=now)
    with pytest.raises(RuntimeError):
        await breaker.call(fail_call, now_seconds=now + 1)
    with pytest.raises(CircuitOpenError):
        await breaker.call(fail_call, now_seconds=now + 2)


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_timeout() -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=10)
    now = 100.0

    async def fail_call() -> str:
        raise RuntimeError("external failure")

    async def success_call() -> str:
        return "ok"

    with pytest.raises(RuntimeError):
        await breaker.call(fail_call, now_seconds=now)
    with pytest.raises(CircuitOpenError):
        await breaker.call(success_call, now_seconds=now + 1)

    result = await breaker.call(success_call, now_seconds=now + 11)
    assert result == "ok"


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_success() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=10)
    now = 100.0

    async def fail_call() -> str:
        raise RuntimeError("external failure")

    async def success_call() -> str:
        return "ok"

    with pytest.raises(RuntimeError):
        await breaker.call(fail_call, now_seconds=now)
    result = await breaker.call(success_call, now_seconds=now + 1)
    assert result == "ok"

    with pytest.raises(RuntimeError):
        await breaker.call(fail_call, now_seconds=now + 2)

