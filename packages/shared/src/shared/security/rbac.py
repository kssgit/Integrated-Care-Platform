from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    GUARDIAN = "guardian"
    FACILITY_ADMIN = "facility_admin"
    CARE_WORKER = "care_worker"
    ADMIN = "admin"


def ensure_roles(role: str, allowed: set[Role]) -> bool:
    try:
        parsed = Role(role)
    except ValueError:
        return False
    return parsed in allowed

