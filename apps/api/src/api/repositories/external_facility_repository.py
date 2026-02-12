from __future__ import annotations

from api.clients.facility_provider_client import FacilityProviderClient
from api.repositories.facility_repository import FacilityEntity


class ExternalFacilityRepository:
    def __init__(self, client: FacilityProviderClient) -> None:
        self._client = client

    async def list_facilities(
        self,
        page: int,
        page_size: int,
        district_code: str | None,
    ) -> tuple[list[FacilityEntity], int]:
        rows, total = await self._client.fetch_facilities(
            page=page,
            page_size=page_size,
            district_code=district_code,
        )
        entities = [
            FacilityEntity(
                id=str(item["id"]),
                name=str(item["name"]),
                district_code=str(item["district_code"]),
            )
            for item in rows
        ]
        return entities, total

