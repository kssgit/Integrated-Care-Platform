from __future__ import annotations


def configure_otel(service_name: str) -> None:
    from devkit.observability import configure_otel as _configure_otel

    _configure_otel(service_name)


def configure_probe_access_log_filter() -> None:
    from devkit.observability import configure_probe_access_log_filter as _configure_probe_access_log_filter

    _configure_probe_access_log_filter()
