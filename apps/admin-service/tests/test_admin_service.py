from __future__ import annotations

from fastapi.testclient import TestClient

from admin_service.app import create_app
from admin_service.store import FacilityPatchAuditRecord, PipelineRunAuditRecord
from shared.security import JWTManager


class StubStore:
    def __init__(self) -> None:
        self.patch_calls: list[dict] = []
        self.pipeline_calls: list[dict] = []

    async def close(self) -> None:
        return None

    async def patch_facility(self, *, facility_id: str, patch: dict, reason: str, actor_user_id: str):
        self.patch_calls.append(
            {"facility_id": facility_id, "patch": patch, "reason": reason, "actor_user_id": actor_user_id}
        )
        return (
            {
                "facility_id": facility_id,
                "name": "patched",
                "district_code": "11110",
                "address": "Seoul",
                "lat": 37.5,
                "lng": 126.9,
                "metadata": {},
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            FacilityPatchAuditRecord(
                facility_id=facility_id,
                actor_user_id=actor_user_id,
                reason=reason,
                applied_fields=sorted(list(patch.keys())),
                patch=patch,
                created_at="2026-01-01T00:00:00+00:00",
            ),
        )

    async def list_facility_patch_audit(self, facility_id: str) -> list[FacilityPatchAuditRecord]:
        return [
            FacilityPatchAuditRecord(
                facility_id=facility_id,
                actor_user_id="admin-1",
                reason="fix typo",
                applied_fields=["name"],
                patch={"name": "new-name"},
                created_at="2026-01-01T00:00:00+00:00",
            )
        ]

    async def add_pipeline_run_audit(self, **kwargs):
        self.pipeline_calls.append(kwargs)
        return PipelineRunAuditRecord(
            action=str(kwargs["action"]),
            dag_id=str(kwargs["dag_id"]),
            dag_run_id=str(kwargs["dag_run_id"]),
            state=str(kwargs["state"]),
            provider=kwargs.get("provider"),
            conf=kwargs.get("conf", {}),
            requested_by=str(kwargs["requested_by"]),
            created_at="2026-01-01T00:00:00+00:00",
        )

    async def list_pipeline_run_audit(self, *, status, provider, from_at, to_at) -> list[PipelineRunAuditRecord]:
        del status, provider, from_at, to_at
        return [
            PipelineRunAuditRecord(
                action="trigger",
                dag_id="seoul_care_plus_daily_sync",
                dag_run_id="admin-test-1",
                state="queued",
                provider="seoul_open_data",
                conf={"provider_name": "seoul_open_data"},
                requested_by="admin-1",
                created_at="2026-01-01T00:00:00+00:00",
            )
        ]


class StubAirflowClient:
    dag_id = "seoul_care_plus_daily_sync"

    async def trigger_dag_run(self, conf: dict, dag_run_id: str | None = None) -> dict:
        return {"dag_run_id": dag_run_id or "admin-test-run", "state": "queued", "conf": conf}

    async def get_dag_run(self, dag_run_id: str) -> dict:
        return {
            "dag_run_id": dag_run_id,
            "state": "success",
            "start_date": "2026-01-01T00:00:00+00:00",
            "end_date": "2026-01-01T00:05:00+00:00",
            "conf": {"provider_name": "seoul_open_data", "start_page": 1, "end_page": 1},
        }


def _admin_token() -> str:
    jwt = JWTManager(secret="dev-only-secret")
    return jwt.issue_access_token(subject="admin-1", role="admin", jti="jti-admin-1")


def _guardian_token() -> str:
    jwt = JWTManager(secret="dev-only-secret")
    return jwt.issue_access_token(subject="user-1", role="guardian", jti="jti-user-1")


def test_admin_role_is_required_for_patch() -> None:
    app = create_app()
    app.state.store = StubStore()
    app.state.airflow_client = StubAirflowClient()
    client = TestClient(app)

    response = client.post(
        "/v1/admin/facilities/fac-1/patch",
        headers={"Authorization": f"Bearer {_guardian_token()}"},
        json={"name": "patched-name", "reason": "fix"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_patch_facility_success() -> None:
    app = create_app()
    app.state.store = StubStore()
    app.state.airflow_client = StubAirflowClient()
    client = TestClient(app)

    response = client.post(
        "/v1/admin/facilities/fac-1/patch",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        json={"name": "patched-name", "reason": "fix"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["facility_id"] == "fac-1"
    assert "name" in body["applied_fields"]
    assert body["updated_by"] == "admin-1"


def test_trigger_and_get_pipeline_run() -> None:
    app = create_app()
    app.state.store = StubStore()
    app.state.airflow_client = StubAirflowClient()
    client = TestClient(app)

    trigger = client.post(
        "/v1/admin/pipeline/runs",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        json={"provider_name": "seoul_open_data", "start_page": 1, "end_page": 1, "dry_run": False},
    )
    assert trigger.status_code == 200
    dag_run_id = trigger.json()["data"]["dag_run_id"]

    get_run = client.get(
        f"/v1/admin/pipeline/runs/{dag_run_id}",
        headers={"Authorization": f"Bearer {_admin_token()}"},
    )
    assert get_run.status_code == 200
    assert get_run.json()["data"]["state"] == "success"


def test_list_pipeline_run_audit() -> None:
    app = create_app()
    app.state.store = StubStore()
    app.state.airflow_client = StubAirflowClient()
    client = TestClient(app)

    response = client.get(
        "/v1/admin/pipeline/runs",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        params={"status": "queued", "provider": "seoul_open_data"},
    )
    assert response.status_code == 200
    assert response.json()["meta"]["count"] == 1
