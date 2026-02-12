from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass

_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def set_trace_id(trace_id: str) -> None:
    _trace_id_ctx.set(trace_id)


def get_trace_id() -> str:
    return _trace_id_ctx.get()


@dataclass(frozen=True)
class ApiRequestMetric:
    method: str
    path: str
    status_code: int
    duration_ms: float
    trace_id: str


class InMemoryApiMetricsCollector:
    def __init__(self) -> None:
        self._metrics: list[ApiRequestMetric] = []

    def observe(self, metric: ApiRequestMetric) -> None:
        self._metrics.append(metric)

    def snapshot(self) -> list[dict]:
        return [asdict(item) for item in self._metrics]

