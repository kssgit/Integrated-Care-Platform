from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from api.errors import ApiError
from api.middleware import ObservabilityMiddleware
from api.observability import (
    CompositeApiMetricsCollector,
    InMemoryApiMetricsCollector,
    PrometheusApiMetricsCollector,
)
from api.response import error_response, success_response
from api.routers.facilities import router as facilities_router
from api.routers.geo import router as geo_router
from api.routers.internal_events import router as internal_events_router
from api.routers.auth_gateway import router as auth_gateway_router
from api.routers.search_gateway import router as search_gateway_router
from api.routers.trust_safety import router as trust_safety_router
from api.routers.users_gateway import router as users_gateway_router
from api.telemetry import configure_otel, configure_probe_access_log_filter


def create_app() -> FastAPI:
    app = FastAPI(title="Integrated Care API", version="0.1.0")
    configure_otel(service_name="integrated-care-api")
    configure_probe_access_log_filter()
    app.state.api_metrics = InMemoryApiMetricsCollector()
    app.state.prom_metrics = PrometheusApiMetricsCollector()
    app.state.composite_metrics = CompositeApiMetricsCollector(
        [app.state.api_metrics, app.state.prom_metrics]
    )
    app.add_middleware(ObservabilityMiddleware, collector=app.state.composite_metrics)
    app.include_router(auth_gateway_router)
    app.include_router(users_gateway_router)
    app.include_router(facilities_router)
    app.include_router(search_gateway_router)
    app.include_router(geo_router)
    app.include_router(internal_events_router)
    app.include_router(trust_safety_router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict:
        return success_response({"status": "ready"}, meta={})

    @app.get("/metrics")
    async def metrics() -> Response:
        payload = app.state.prom_metrics.render()
        return Response(content=payload, media_type="text/plain; version=0.0.4")

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(err["msg"] for err in exc.errors())
        return JSONResponse(
            status_code=422,
            content=error_response("VALIDATION_ERROR", message),
        )

    return app


app = create_app()
