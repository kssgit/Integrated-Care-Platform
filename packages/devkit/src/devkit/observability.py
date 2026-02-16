from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

_configured = False
_probe_filter_configured = False


class _ProbeAccessLogFilter(logging.Filter):
    def __init__(self, ignored_paths: tuple[str, ...]) -> None:
        super().__init__()
        self._ignored_paths = {self._normalize_path(path) for path in ignored_paths}

    @staticmethod
    def _normalize_path(path: str) -> str:
        base = path.split("?", 1)[0]
        if base != "/" and base.endswith("/"):
            return base[:-1]
        return base

    @classmethod
    def _extract_path_and_status(cls, record: logging.LogRecord) -> tuple[str | None, int | None]:
        args: Any = getattr(record, "args", ())
        if not isinstance(args, tuple) or len(args) < 5:
            return None, None
        path = args[2] if len(args) > 2 and isinstance(args[2], str) else None
        status_raw = args[4] if len(args) > 4 else None
        try:
            status = int(status_raw) if status_raw is not None else None
        except (TypeError, ValueError):
            status = None
        return path, status

    def filter(self, record: logging.LogRecord) -> bool:
        path, status = self._extract_path_and_status(record)
        if path is None or status is None:
            return True
        normalized_path = self._normalize_path(path)
        if status == 200 and normalized_path in self._ignored_paths:
            return False
        return True


def configure_otel(service_name: str) -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    trace.set_tracer_provider(provider)
    _configured = True


def configure_probe_access_log_filter(ignored_paths: tuple[str, ...] = ("/healthz", "/readyz")) -> None:
    global _probe_filter_configured
    if _probe_filter_configured:
        return
    logging.getLogger("uvicorn.access").addFilter(_ProbeAccessLogFilter(ignored_paths=ignored_paths))
    _probe_filter_configured = True
