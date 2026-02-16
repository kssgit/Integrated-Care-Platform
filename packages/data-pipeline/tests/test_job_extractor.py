from __future__ import annotations

import httpx
import pytest

from data_pipeline.jobs.extractor import ProviderFacilityExtractor


@pytest.mark.asyncio
async def test_provider_facility_extractor_reads_multiple_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "id": f"id-{page}",
                        "name": f"Center {page}",
                        "address": "Seoul",
                        "district_code": "11110",
                        "lat": 37.5,
                        "lng": 126.9,
                        "source_updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    extractor = ProviderFacilityExtractor(
        base_url="https://provider.example.com",
        start_page=1,
        end_page=2,
        client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
    )
    rows = await extractor.extract()

    assert len(rows) == 2
    assert rows[0]["source_id"] == "id-1"
    assert rows[1]["source_id"] == "id-2"


@pytest.mark.asyncio
async def test_provider_facility_extractor_uses_custom_endpoint_path() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "id": "id-1",
                        "name": "Center 1",
                        "address": "Seoul",
                        "district_code": "11110",
                        "lat": 37.5,
                        "lng": 126.9,
                        "source_updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    extractor = ProviderFacilityExtractor(
        base_url="https://provider.example.com",
        endpoint_path="/national/facilities",
        start_page=1,
        end_page=1,
        client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
    )
    rows = await extractor.extract()

    assert len(rows) == 1
    assert requested_paths == ["/national/facilities"]


@pytest.mark.asyncio
async def test_provider_facility_extractor_supports_provider_alias_fields() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "facility_id": "mo-1",
                        "facility_name": "MOHW Center",
                        "road_address": "Seoul Jongno-gu",
                        "sigungu_code": "11110",
                        "latitude": "37.57",
                        "longitude": "126.98",
                        "last_modified_at": "2026-01-02T00:00:00+00:00",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    extractor = ProviderFacilityExtractor(
        base_url="https://provider.example.com",
        endpoint_path="/mohw/facilities",
        start_page=1,
        end_page=1,
        client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
    )
    rows = await extractor.extract()

    assert len(rows) == 1
    assert rows[0]["source_id"] == "mo-1"
    assert rows[0]["name"] == "MOHW Center"
    assert rows[0]["district_code"] == "11110"
    assert rows[0]["lat"] == 37.57
    assert rows[0]["lng"] == 126.98


@pytest.mark.asyncio
async def test_provider_facility_extractor_maps_invalid_coordinates_to_reject_values() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "id": "bad-1",
                        "name": "Invalid Coordinates",
                        "address": "Unknown",
                        "district_code": "00000",
                        "lat": "not-a-float",
                        "lng": None,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    extractor = ProviderFacilityExtractor(
        base_url="https://provider.example.com",
        start_page=1,
        end_page=1,
        client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
    )
    rows = await extractor.extract()

    assert len(rows) == 1
    assert rows[0]["lat"] == 999.0
    assert rows[0]["lng"] == 999.0
