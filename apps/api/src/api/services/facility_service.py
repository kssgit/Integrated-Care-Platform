from __future__ import annotations

from typing import Protocol

from api.schemas.facility import FacilityItem, FacilityListQuery


class FacilityRepositoryLike(Protocol):
    async def list_facilities(
        self,
        page: int,
        page_size: int,
        district_code: str | None,
    ) -> tuple[list, int]: ...


class FacilityService:
    def __init__(self, repository: FacilityRepositoryLike) -> None:
        self._repository = repository

    async def list_facilities(self, query: FacilityListQuery) -> tuple[list[FacilityItem], int]:
        rows, total = await self._repository.list_facilities(
            page=query.page,
            page_size=query.page_size,
            district_code=query.district_code,
        )
        return [FacilityItem(id=row.id, name=row.name, district_code=row.district_code) for row in rows], total
