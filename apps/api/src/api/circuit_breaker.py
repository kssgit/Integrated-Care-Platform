from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when calls are blocked by an open circuit."""


@dataclass
class CircuitBreakerState:
    failure_count: int = 0
    opened_at_seconds: float | None = None


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 30,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout_seconds = recovery_timeout_seconds
        self._state = CircuitBreakerState()

    async def call(
        self,
        operation: Callable[[], Awaitable[T]],
        now_seconds: float,
    ) -> T:
        if self._is_open(now_seconds):
            logger.warning("circuit_open", extra={"component": "api", "now_seconds": now_seconds})
            raise CircuitOpenError("circuit is open")

        try:
            result = await operation()
        except Exception:
            self._record_failure(now_seconds)
            raise
        self._record_success()
        return result

    def _is_open(self, now_seconds: float) -> bool:
        opened_at = self._state.opened_at_seconds
        if opened_at is None:
            return False
        if now_seconds - opened_at >= self._recovery_timeout_seconds:
            self._state.opened_at_seconds = None
            self._state.failure_count = 0
            logger.info("circuit_half_open", extra={"component": "api"})
            return False
        return True

    def _record_failure(self, now_seconds: float) -> None:
        self._state.failure_count += 1
        if self._state.failure_count >= self._failure_threshold:
            self._state.opened_at_seconds = now_seconds
            logger.error(
                "circuit_opened",
                extra={
                    "component": "api",
                    "failure_count": self._state.failure_count,
                    "opened_at_seconds": now_seconds,
                },
            )

    def _record_success(self) -> None:
        self._state.failure_count = 0
        self._state.opened_at_seconds = None

