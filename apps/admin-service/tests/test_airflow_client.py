from __future__ import annotations

import httpx
import pytest

from admin_service.airflow_client import AirflowClient, AirflowClientConfig, AirflowClientError


@pytest.mark.asyncio
async def test_airflow_client_maps_401_to_unauthorized(monkeypatch) -> None:
    async def _request(self, method, url, json=None, auth=None):  # noqa: ANN001
        request = httpx.Request(method=method, url=url)
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(httpx.AsyncClient, "request", _request, raising=True)
    client = AirflowClient(
        AirflowClientConfig(
            base_url="http://airflow.local",
            username="admin",
            password="password",
            max_retries=1,
        )
    )

    with pytest.raises(AirflowClientError) as exc_info:
        await client.get_dag_run("run-1")

    assert exc_info.value.code == "AIRFLOW_UNAUTHORIZED"
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_airflow_client_maps_timeout(monkeypatch) -> None:
    async def _request(self, method, url, json=None, auth=None):  # noqa: ANN001
        request = httpx.Request(method=method, url=url)
        raise httpx.TimeoutException("timeout", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "request", _request, raising=True)
    client = AirflowClient(
        AirflowClientConfig(
            base_url="http://airflow.local",
            username="admin",
            password="password",
            max_retries=1,
        )
    )

    with pytest.raises(AirflowClientError) as exc_info:
        await client.trigger_dag_run(conf={"provider_name": "seoul_open_data"})

    assert exc_info.value.code == "AIRFLOW_TIMEOUT"
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_airflow_client_maps_404_to_not_found(monkeypatch) -> None:
    async def _request(self, method, url, json=None, auth=None):  # noqa: ANN001
        request = httpx.Request(method=method, url=url)
        return httpx.Response(status_code=404, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "request", _request, raising=True)
    client = AirflowClient(
        AirflowClientConfig(
            base_url="http://airflow.local",
            username="admin",
            password="password",
            max_retries=1,
        )
    )

    with pytest.raises(AirflowClientError) as exc_info:
        await client.get_dag_run("missing-run")

    assert exc_info.value.code == "AIRFLOW_NOT_FOUND"
    assert exc_info.value.status_code == 404
