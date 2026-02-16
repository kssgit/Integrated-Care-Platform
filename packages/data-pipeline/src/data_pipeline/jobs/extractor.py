from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from data_pipeline.core.pipeline import Extractor


def _parse_source_updated_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return datetime.now(timezone.utc)


def _pick(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _to_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _to_float_or_reject(value: Any, invalid_value: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return invalid_value


class ProviderFacilityExtractor(Extractor[dict]):
    def __init__(
        self,
        base_url: str,
        page_size: int = 200,
        start_page: int = 1,
        end_page: int = 1,
        endpoint_path: str = "/facilities",
        timeout_seconds: float = 5.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._page_size = page_size
        self._start_page = start_page
        self._end_page = end_page
        self._endpoint_path = endpoint_path
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory

    async def extract(self) -> list[dict]:
        rows: list[dict] = []
        factory = self._client_factory or (lambda: httpx.AsyncClient(timeout=self._timeout_seconds))
        async with factory() as client:
            for page in range(self._start_page, self._end_page + 1):
                batch = await self._fetch_page(client, page)
                rows.extend(batch)
        return rows

    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> list[dict]:
        response = await client.get(
            f"{self._base_url}{self._endpoint_path}",
            params={"page": page, "page_size": self._page_size},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        return [self._to_record(item) for item in items]

    def _to_record(self, item: dict) -> dict:
        source_id = _pick(item, "source_id", "id", "facility_id", "inst_id", "svc_id")
        name = _pick(item, "name", "facility_name", "institution_name", "svc_nm")
        address = _pick(item, "address", "road_address", "addr", "jibun_address")
        district_code = _pick(item, "district_code", "gu_code", "sigungu_code", "district")
        lat = _pick(item, "lat", "latitude", "y", "wgs84_lat")
        lng = _pick(item, "lng", "longitude", "x", "wgs84_lng")
        source_updated_at = _pick(item, "source_updated_at", "updated_at", "last_modified_at")
        return {
            "source_id": _to_str(source_id, default=""),
            "name": _to_str(name, default=""),
            "address": _to_str(address, default=""),
            "district_code": _to_str(district_code, default=""),
            # Parsing failure intentionally maps to out-of-range values
            # so quality gate can reject the record without crashing extraction.
            "lat": _to_float_or_reject(lat, invalid_value=999.0),
            "lng": _to_float_or_reject(lng, invalid_value=999.0),
            "source_updated_at": _parse_source_updated_at(source_updated_at),
        }
