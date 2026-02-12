from __future__ import annotations

import httpx
import pytest

from api.clients.facility_provider_client import FacilityProviderClient
from api.errors import ApiError


def build_client(handler):
    transport = httpx.MockTransport(handler)
    return FacilityProviderClient(
        base_url="https://provider.example.com",
        timeout_seconds=5.0,
        client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
    )


@pytest.mark.asyncio
async def test_facility_provider_client_parses_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/facilities"
        return httpx.Response(
            status_code=200,
            json={
                "data": [{"id": "f-1", "name": "Center", "district_code": "11110"}],
                "meta": {"total": 1},
            },
        )

    client = build_client(handler)
    rows, total = await client.fetch_facilities(page=1, page_size=20, district_code=None)

    assert total == 1
    assert rows[0]["id"] == "f-1"


@pytest.mark.asyncio
async def test_facility_provider_client_maps_http_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, json={"message": "down"})

    client = build_client(handler)
    with pytest.raises(ApiError) as exc_info:
        await client.fetch_facilities(page=1, page_size=20, district_code=None)

    assert exc_info.value.code == "UPSTREAM_HTTP_ERROR"

