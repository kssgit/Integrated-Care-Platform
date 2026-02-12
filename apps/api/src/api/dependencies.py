from __future__ import annotations

import os

from api.cache import FacilityCache, InMemoryCacheStore, RedisCacheStore
from api.circuit_breaker import CircuitBreaker
from api.clients.facility_provider_client import FacilityProviderClient
from api.rate_limit import InMemoryRateLimitStore, RedisRateLimitStore, SlidingWindowRateLimiter
from api.repositories.external_facility_repository import ExternalFacilityRepository
from api.repositories.facility_repository import FacilityRepository
from api.services.facility_service import FacilityService

provider_base_url = os.getenv("FACILITY_PROVIDER_BASE_URL")
if provider_base_url:
    _facility_repository = ExternalFacilityRepository(
        FacilityProviderClient(base_url=provider_base_url, timeout_seconds=5.0),
    )
else:
    _facility_repository = FacilityRepository()

_facility_service = FacilityService(_facility_repository)
redis_url = os.getenv("REDIS_URL")
if redis_url:
    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        _rate_limit_store = RedisRateLimitStore(redis_client, window_seconds=60)
        _facility_cache_store = RedisCacheStore(redis_client)
    except Exception:
        _rate_limit_store = InMemoryRateLimitStore()
        _facility_cache_store = InMemoryCacheStore()
else:
    _rate_limit_store = InMemoryRateLimitStore()
    _facility_cache_store = InMemoryCacheStore()
_rate_limiter = SlidingWindowRateLimiter(_rate_limit_store, limit_per_minute=100, window_seconds=60)
_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30)
_facility_cache = FacilityCache(
    store=_facility_cache_store,
    ttl_seconds=int(os.getenv("API_CACHE_TTL_SECONDS", "30")),
)


def get_facility_service() -> FacilityService:
    return _facility_service


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _rate_limiter


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker


def get_facility_cache() -> FacilityCache:
    return _facility_cache
