from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class SafeNumberGateway(Protocol):
    async def allocate_relay_number(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int,
    ) -> str: ...


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        raise ValueError("phone must contain at least 10 digits")
    return digits


def mask_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) <= 6:
        return "*" * len(normalized)
    return f"{normalized[:3]}****{normalized[-3:]}"


@dataclass(frozen=True)
class SafeNumberRoute:
    relay_number: str
    masked_caller: str
    masked_callee: str
    expires_at: datetime


class InMemorySafeNumberGateway:
    async def allocate_relay_number(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int,
    ) -> str:
        caller = normalize_phone(caller_phone)
        callee = normalize_phone(callee_phone)
        digest = hashlib.sha256(f"{caller}:{callee}:{ttl_minutes}".encode("utf-8")).hexdigest()
        suffix = str(int(digest[:8], 16)).zfill(10)[-8:]
        return f"050-{suffix[:4]}-{suffix[4:]}"


class SafeNumberRouter:
    def __init__(self, gateway: SafeNumberGateway) -> None:
        self._gateway = gateway

    async def route(
        self,
        caller_phone: str,
        callee_phone: str,
        ttl_minutes: int = 30,
    ) -> SafeNumberRoute:
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be > 0")
        relay = await self._gateway.allocate_relay_number(caller_phone, callee_phone, ttl_minutes)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        return SafeNumberRoute(
            relay_number=relay,
            masked_caller=mask_phone(caller_phone),
            masked_callee=mask_phone(callee_phone),
            expires_at=expires_at,
        )

