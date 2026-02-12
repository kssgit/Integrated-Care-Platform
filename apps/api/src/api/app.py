from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.errors import ApiError
from api.response import error_response, success_response
from api.routers.facilities import router as facilities_router


def create_app() -> FastAPI:
    app = FastAPI(title="Integrated Care API", version="0.1.0")
    app.include_router(facilities_router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return success_response({"status": "ok"}, meta={})

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

