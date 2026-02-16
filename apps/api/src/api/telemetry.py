from __future__ import annotations

def configure_otel(service_name: str) -> None:
    from devkit.observability import configure_otel as _configure_otel

    _configure_otel(service_name)
