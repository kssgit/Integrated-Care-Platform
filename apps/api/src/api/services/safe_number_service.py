from __future__ import annotations

from pydantic import BaseModel

from api.repositories.safe_number_repository import SafeNumberRepository


class SafeNumberRouteItem(BaseModel):
    relay_number: str
    masked_caller: str
    masked_callee: str
    expires_at: str


class SafeNumberService:
    def __init__(self, repository: SafeNumberRepository) -> None:
        self._repository = repository

    async def create_route(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int,
    ) -> SafeNumberRouteItem:
        route = await self._repository.create_route(caller_phone, callee_phone, ttl_minutes)
        return SafeNumberRouteItem(
            relay_number=route.relay_number,
            masked_caller=route.masked_caller,
            masked_callee=route.masked_callee,
            expires_at=route.expires_at.isoformat(),
        )

