from __future__ import annotations

import logging

from devkit.observability import _ProbeAccessLogFilter


def _access_record(path: str, status: int) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:12345", "GET", path, "1.1", status),
        exc_info=None,
    )


def test_probe_access_log_filter_ignores_probe_200() -> None:
    probe_filter = _ProbeAccessLogFilter(ignored_paths=("/healthz", "/readyz"))
    assert probe_filter.filter(_access_record("/healthz", 200)) is False
    assert probe_filter.filter(_access_record("/readyz", 200)) is False
    assert probe_filter.filter(_access_record("/readyz?full=true", 200)) is False


def test_probe_access_log_filter_keeps_non_probe_or_non_200() -> None:
    probe_filter = _ProbeAccessLogFilter(ignored_paths=("/healthz", "/readyz"))
    assert probe_filter.filter(_access_record("/healthz", 500)) is True
    assert probe_filter.filter(_access_record("/v1/users", 200)) is True
