from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.observability import ApiMetricCollector, ApiRequestMetric, set_trace_id


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, collector: ApiMetricCollector) -> None:
        super().__init__(app)
        self._collector = collector
        self._tracer = trace.get_tracer("integrated-care-api")

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        set_trace_id(trace_id)
        started = perf_counter()
        with self._tracer.start_as_current_span("http.request") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", request.url.path)
            span.set_attribute("trace.id", trace_id)
            try:
                response = await call_next(request)
            except Exception:
                self._collector.observe(
                    ApiRequestMetric(
                        method=request.method,
                        path=request.url.path,
                        status_code=500,
                        duration_ms=(perf_counter() - started) * 1000.0,
                        trace_id=trace_id,
                    )
                )
                span.set_attribute("http.status_code", 500)
                raise
            span.set_attribute("http.status_code", response.status_code)

        response.headers["x-trace-id"] = trace_id
        self._collector.observe(
            ApiRequestMetric(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=(perf_counter() - started) * 1000.0,
                trace_id=trace_id,
            )
        )
        return response
