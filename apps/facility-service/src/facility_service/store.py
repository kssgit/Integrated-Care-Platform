from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Facility:
    facility_id: str
    name: str
    district_code: str
    address: str
    lat: float
    lng: float
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FacilityStore:
    def __init__(self) -> None:
        self._items: dict[str, Facility] = {
            "fac-1": Facility(
                facility_id="fac-1",
                name="Jongno Care Center",
                district_code="11110",
                address="Jongno-gu, Seoul",
                lat=37.572,
                lng=126.979,
            ),
            "fac-2": Facility(
                facility_id="fac-2",
                name="Mapo Family Hub",
                district_code="11440",
                address="Mapo-gu, Seoul",
                lat=37.566,
                lng=126.901,
            ),
            "fac-3": Facility(
                facility_id="fac-3",
                name="Gangnam Senior Link",
                district_code="11680",
                address="Gangnam-gu, Seoul",
                lat=37.497,
                lng=127.028,
            ),
        }
        self._sync_log: list[dict[str, str]] = []

    async def list_facilities(
        self,
        *,
        page: int,
        page_size: int,
        district_code: str | None = None,
    ) -> tuple[list[Facility], int]:
        items = [item for item in self._items.values() if not district_code or item.district_code == district_code]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def get_by_id(self, facility_id: str) -> Facility | None:
        return self._items.get(facility_id)

    async def search(self, query: str, district_code: str | None = None) -> list[Facility]:
        q = query.lower().strip()
        return [
            item
            for item in self._items.values()
            if (not district_code or item.district_code == district_code)
            and (q in item.name.lower() or q in item.address.lower())
        ]

    async def upsert(self, facility: Facility, source: str = "unknown") -> Facility:
        self._items[facility.facility_id] = facility
        self._sync_log.append(
            {
                "facility_id": facility.facility_id,
                "source": source,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return facility

