from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class AirflowClientConfig:
    base_url: str
    username: str
    password: str
    dag_id: str = "seoul_care_plus_daily_sync"
    timeout_seconds: float = 5.0


class AirflowClientError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class AirflowClient:
    def __init__(self, config: AirflowClientConfig) -> None:
        self._config = config

    @property
    def dag_id(self) -> str:
        return self._config.dag_id

    async def trigger_dag_run(self, conf: dict[str, Any], dag_run_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"conf": conf}
        if dag_run_id:
            payload["dag_run_id"] = dag_run_id
        return await self._request(
            "POST",
            f"/api/v1/dags/{self._config.dag_id}/dagRuns",
            json=payload,
        )

    async def get_dag_run(self, dag_run_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/v1/dags/{self._config.dag_id}/dagRuns/{dag_run_id}")

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        base = self._config.base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=f"{base}{path}",
                    json=json,
                    auth=(self._config.username, self._config.password),
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AirflowClientError("AIRFLOW_TIMEOUT", "Airflow request timed out", 504) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {401, 403}:
                raise AirflowClientError("AIRFLOW_UNAUTHORIZED", "Airflow auth failed", 502) from exc
            raise AirflowClientError("AIRFLOW_HTTP_ERROR", "Airflow returned an error", 502) from exc
        except httpx.HTTPError as exc:
            raise AirflowClientError("AIRFLOW_UNAVAILABLE", "Airflow request failed", 502) from exc
        return response.json()
