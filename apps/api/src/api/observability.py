from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass
from typing import Protocol

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

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


class ApiMetricCollector(Protocol):
    def observe(self, metric: ApiRequestMetric) -> None: ...


class InMemoryApiMetricsCollector(ApiMetricCollector):
    def __init__(self) -> None:
        self._metrics: list[ApiRequestMetric] = []

    def observe(self, metric: ApiRequestMetric) -> None:
        self._metrics.append(metric)

    def snapshot(self) -> list[dict]:
        return [asdict(item) for item in self._metrics]


class PrometheusApiMetricsCollector(ApiMetricCollector):
    def __init__(self) -> None:
        self._registry = CollectorRegistry()
        self._request_counter = Counter(
            "api_http_requests_total",
            "Total API HTTP requests",
            labelnames=("method", "path", "status_code"),
            registry=self._registry,
        )
        self._latency_histogram = Histogram(
            "api_http_request_duration_ms",
            "API HTTP request latency in milliseconds",
            labelnames=("method", "path"),
            buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 3000),
            registry=self._registry,
        )

    def observe(self, metric: ApiRequestMetric) -> None:
        status = str(metric.status_code)
        self._request_counter.labels(metric.method, metric.path, status).inc()
        self._latency_histogram.labels(metric.method, metric.path).observe(metric.duration_ms)

    def render(self) -> str:
        return generate_latest(self._registry).decode("utf-8")


class CompositeApiMetricsCollector(ApiMetricCollector):
    def __init__(self, collectors: list[ApiMetricCollector]) -> None:
        self._collectors = collectors

    def observe(self, metric: ApiRequestMetric) -> None:
        for collector in self._collectors:
            collector.observe(metric)
