from __future__ import annotations

from datetime import datetime
from contextlib import asynccontextmanager
import os
from uuid import uuid4

from devkit.config import load_settings
from devkit.observability import configure_otel, configure_probe_access_log_filter
from devkit.timezone import now_kst_iso
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from admin_service.airflow_client import AirflowClient, AirflowClientConfig, AirflowClientError
from admin_service.response import error_response, success_response
from admin_service.schemas import FacilityPatchRequest, PipelineRunTriggerRequest
from admin_service.store import AdminStore
from shared.security import JWTManager, Role, ensure_roles


def _build_airflow_client() -> AirflowClient | None:
    base_url = os.getenv("AIRFLOW_API_BASE_URL")
    username = os.getenv("AIRFLOW_API_USERNAME")
    password = os.getenv("AIRFLOW_API_PASSWORD")
    dag_id = os.getenv("AIRFLOW_DAG_ID", "seoul_care_plus_daily_sync")
    timeout_seconds = float(os.getenv("AIRFLOW_API_TIMEOUT_SECONDS", "5.0"))
    max_retries = int(os.getenv("AIRFLOW_API_MAX_RETRIES", "3"))
    retry_base_delay_seconds = float(os.getenv("AIRFLOW_API_RETRY_BASE_DELAY_SECONDS", "0.2"))
    if not base_url or not username or not password:
        return None
    return AirflowClient(
        AirflowClientConfig(
            base_url=base_url,
            username=username,
            password=password,
            dag_id=dag_id,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
        )
    )


def create_app() -> FastAPI:
    settings = load_settings("admin-service")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await app.state.store.close()

    app = FastAPI(title="Admin Service", version="0.1.0", lifespan=lifespan)
    configure_otel(service_name="admin-service")
    configure_probe_access_log_filter()

    app.state.jwt = JWTManager(secret=settings.JWT_SECRET_KEY)
    app.state.store = AdminStore(settings.DATABASE_URL)
    app.state.airflow_client = _build_airflow_client()

    async def resolve_auth(authorization: str | None = Header(default=None)) -> dict[str, str]:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "missing bearer token"},
            )
        token = authorization.split(" ", 1)[1]
        try:
            payload = app.state.jwt.decode(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            ) from exc
        if not ensure_roles(payload.role, {Role.ADMIN}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "admin role required"},
            )
        return {"user_id": payload.sub, "role": payload.role}

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            payload = {"success": False, "error": exc.detail}
        else:
            payload = error_response("HTTP_ERROR", str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict[str, object]:
        return success_response({"status": "ready"}, meta={})

    @app.post("/v1/admin/facilities/{facility_id}/patch")
    async def patch_facility(
        facility_id: str,
        body: FacilityPatchRequest,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        patch = body.model_dump(exclude_none=True)
        reason = str(patch.pop("reason"))
        if not patch:
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "no patch field provided"})

        try:
            facility, audit = await app.state.store.patch_facility(
                facility_id=facility_id,
                patch=patch,
                reason=reason,
                actor_user_id=auth["user_id"],
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "STORE_UNAVAILABLE", "message": str(exc)}) from exc

        return success_response(
            {
                "facility_id": facility["facility_id"],
                "applied_fields": audit.applied_fields,
                "updated_at": facility["updated_at"],
                "updated_by": auth["user_id"],
            },
            meta={},
        )

    @app.get("/v1/admin/facilities/{facility_id}/audit")
    async def facility_audit(
        facility_id: str,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        del auth
        rows = await app.state.store.list_facility_patch_audit(facility_id)
        return success_response(
            [
                {
                    "facility_id": item.facility_id,
                    "actor_user_id": item.actor_user_id,
                    "reason": item.reason,
                    "applied_fields": item.applied_fields,
                    "patch": item.patch,
                    "created_at": item.created_at,
                }
                for item in rows
            ],
            meta={"count": len(rows)},
        )

    @app.post("/v1/admin/pipeline/runs")
    async def trigger_pipeline_run(
        body: PipelineRunTriggerRequest,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        airflow_client = app.state.airflow_client
        if airflow_client is None:
            raise HTTPException(
                status_code=503,
                detail={"code": "AIRFLOW_NOT_CONFIGURED", "message": "airflow client is not configured"},
            )
        conf = {
            "provider_name": body.provider_name,
            "start_page": body.start_page,
            "end_page": body.end_page,
            "dry_run": body.dry_run,
        }
        request_id = str(uuid4())
        run_id = f"admin-{uuid4()}"
        try:
            response = await airflow_client.trigger_dag_run(conf=conf, dag_run_id=run_id)
        except AirflowClientError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc

        dag_run_id = str(response.get("dag_run_id", run_id))
        state = str(response.get("state", "queued"))
        await app.state.store.add_pipeline_run_audit(
            action="trigger",
            dag_id=airflow_client.dag_id,
            dag_run_id=dag_run_id,
            state=state,
            provider=body.provider_name,
            conf=conf,
            requested_by=auth["user_id"],
        )
        return success_response(
            {
                "dag_id": airflow_client.dag_id,
                "dag_run_id": dag_run_id,
                "state": state,
                "triggered_at": now_kst_iso(),
                "request_id": request_id,
            },
            meta={},
        )

    @app.get("/v1/admin/pipeline/runs/{dag_run_id}")
    async def get_pipeline_run(
        dag_run_id: str,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        airflow_client = app.state.airflow_client
        if airflow_client is None:
            raise HTTPException(
                status_code=503,
                detail={"code": "AIRFLOW_NOT_CONFIGURED", "message": "airflow client is not configured"},
            )
        try:
            response = await airflow_client.get_dag_run(dag_run_id=dag_run_id)
        except AirflowClientError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc

        conf = response.get("conf") if isinstance(response.get("conf"), dict) else {}
        state = str(response.get("state", "unknown"))
        await app.state.store.add_pipeline_run_audit(
            action="query",
            dag_id=airflow_client.dag_id,
            dag_run_id=dag_run_id,
            state=state,
            provider=conf.get("provider_name") if isinstance(conf, dict) else None,
            conf=conf,
            requested_by=auth["user_id"],
        )

        return success_response(
            {
                "dag_run_id": dag_run_id,
                "state": state,
                "start_date": response.get("start_date"),
                "end_date": response.get("end_date"),
                "conf": conf,
            },
            meta={},
        )

    @app.post("/v1/admin/pipeline/runs/{dag_run_id}/retry")
    async def retry_pipeline_run(
        dag_run_id: str,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        airflow_client = app.state.airflow_client
        if airflow_client is None:
            raise HTTPException(
                status_code=503,
                detail={"code": "AIRFLOW_NOT_CONFIGURED", "message": "airflow client is not configured"},
            )
        try:
            existing = await airflow_client.get_dag_run(dag_run_id=dag_run_id)
            existing_conf = existing.get("conf") if isinstance(existing.get("conf"), dict) else {}
            new_run_id = f"retry-{uuid4()}"
            response = await airflow_client.trigger_dag_run(conf=existing_conf, dag_run_id=new_run_id)
        except AirflowClientError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc

        retried_run_id = str(response.get("dag_run_id", new_run_id))
        state = str(response.get("state", "queued"))
        provider = existing_conf.get("provider_name") if isinstance(existing_conf, dict) else None
        await app.state.store.add_pipeline_run_audit(
            action="retry",
            dag_id=airflow_client.dag_id,
            dag_run_id=retried_run_id,
            state=state,
            provider=provider,
            conf=existing_conf if isinstance(existing_conf, dict) else {},
            requested_by=auth["user_id"],
        )

        return success_response(
            {
                "dag_run_id": retried_run_id,
                "state": state,
            },
            meta={"retried_from": dag_run_id},
        )

    @app.get("/v1/admin/pipeline/runs")
    async def list_pipeline_runs(
        status_filter: str | None = Query(default=None, alias="status"),
        provider: str | None = Query(default=None),
        from_at: datetime | None = Query(default=None, alias="from"),
        to_at: datetime | None = Query(default=None, alias="to"),
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        del auth
        rows = await app.state.store.list_pipeline_run_audit(
            status=status_filter,
            provider=provider,
            from_at=from_at,
            to_at=to_at,
        )
        return success_response(
            [
                {
                    "action": item.action,
                    "dag_id": item.dag_id,
                    "dag_run_id": item.dag_run_id,
                    "state": item.state,
                    "provider": item.provider,
                    "conf": item.conf,
                    "requested_by": item.requested_by,
                    "created_at": item.created_at,
                }
                for item in rows
            ],
            meta={"count": len(rows)},
        )

    return app


app = create_app()
