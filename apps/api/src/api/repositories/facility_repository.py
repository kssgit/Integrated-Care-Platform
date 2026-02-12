from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FacilityEntity:
    id: str
    name: str
    district_code: str


class FacilityRepository:
    def __init__(self) -> None:
        self._items = [
            FacilityEntity(id="fac-1", name="Jongno Care Center", district_code="11110"),
            FacilityEntity(id="fac-2", name="Mapo Family Hub", district_code="11440"),
            FacilityEntity(id="fac-3", name="Gangnam Senior Link", district_code="11680"),
        ]

    async def list_facilities(
        self,
        page: int,
        page_size: int,
        district_code: str | None,
    ) -> tuple[list[FacilityEntity], int]:
        filtered = [item for item in self._items if not district_code or item.district_code == district_code]
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

