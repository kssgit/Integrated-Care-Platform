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


class ProviderFacilityExtractor(Extractor[dict]):
    def __init__(
        self,
        base_url: str,
        page_size: int = 200,
        start_page: int = 1,
        end_page: int = 1,
        timeout_seconds: float = 5.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._page_size = page_size
        self._start_page = start_page
        self._end_page = end_page
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
            f"{self._base_url}/facilities",
            params={"page": page, "page_size": self._page_size},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        return [self._to_record(item) for item in items]

    def _to_record(self, item: dict) -> dict:
        source_id = item.get("source_id") or item.get("id")
        return {
            "source_id": str(source_id),
            "name": str(item["name"]),
            "address": str(item["address"]),
            "district_code": str(item["district_code"]),
            "lat": float(item["lat"]),
            "lng": float(item["lng"]),
            "source_updated_at": _parse_source_updated_at(item.get("source_updated_at")),
        }
