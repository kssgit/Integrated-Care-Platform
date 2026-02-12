from __future__ import annotations

from api.circuit_breaker import CircuitBreaker
from api.rate_limit import InMemoryRateLimitStore, SlidingWindowRateLimiter
from api.repositories.facility_repository import FacilityRepository
from api.services.facility_service import FacilityService

_facility_repository = FacilityRepository()
_facility_service = FacilityService(_facility_repository)
_rate_limit_store = InMemoryRateLimitStore()
_rate_limiter = SlidingWindowRateLimiter(_rate_limit_store, limit_per_minute=100, window_seconds=60)
_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30)


def get_facility_service() -> FacilityService:
    return _facility_service


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _rate_limiter


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker

