from __future__ import annotations

from devkit.observability import configure_probe_access_log_filter
from fastapi import FastAPI, Response

from data_pipeline.monitoring.state import pipeline_exporter, pipeline_metrics


def create_monitoring_app() -> FastAPI:
    app = FastAPI(title="Data Pipeline Monitoring", version="0.1.0")
    configure_probe_access_log_filter()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        body = pipeline_exporter.render(pipeline_metrics)
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app


app = create_monitoring_app()
