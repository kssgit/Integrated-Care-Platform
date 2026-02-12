from __future__ import annotations

from api.clients.safe_number_provider_client import SafeNumberProviderClient
from trust_safety.safe_number import (
    InMemorySafeNumberGateway,
    SafeNumberGateway,
    SafeNumberRoute,
    SafeNumberRouter,
)


class ProviderSafeNumberGateway:
    def __init__(self, client: SafeNumberProviderClient) -> None:
        self._client = client

    async def allocate_relay_number(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int,
    ) -> str:
        return await self._client.allocate(caller_phone, callee_phone, ttl_minutes)


class SafeNumberRepository:
    def __init__(self, gateway: SafeNumberGateway | None = None) -> None:
        self._router = SafeNumberRouter(gateway=gateway or InMemorySafeNumberGateway())

    async def create_route(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int,
    ) -> SafeNumberRoute:
        return await self._router.route(caller_phone, callee_phone, ttl_minutes)
