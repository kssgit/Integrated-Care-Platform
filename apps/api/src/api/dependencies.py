from __future__ import annotations

import os

from geo_engine.postgis_adapter import PostGISAdapter

from api.cache import FacilityCache, InMemoryCacheStore, RedisCacheStore
from api.circuit_breaker import CircuitBreaker
from api.clients.facility_provider_client import FacilityProviderClient
from api.clients.safe_number_provider_client import SafeNumberProviderClient
from api.rate_limit import InMemoryRateLimitStore, RedisRateLimitStore, SlidingWindowRateLimiter
from api.repositories.external_facility_repository import ExternalFacilityRepository
from api.repositories.facility_repository import FacilityRepository
from api.repositories.safe_number_repository import ProviderSafeNumberGateway, SafeNumberRepository
from api.services.facility_service import FacilityService
from api.services.geo_service import GeoService
from api.services.safe_number_service import SafeNumberService

provider_base_url = os.getenv("FACILITY_PROVIDER_BASE_URL")
if provider_base_url:
    _facility_repository = ExternalFacilityRepository(
        FacilityProviderClient(base_url=provider_base_url, timeout_seconds=5.0),
    )
else:
    _facility_repository = FacilityRepository()

_facility_service = FacilityService(_facility_repository)
database_url = os.getenv("DATABASE_URL")
_geo_postgis_adapter = PostGISAdapter(dsn=database_url) if database_url else None
_geo_service = GeoService(postgis_adapter=_geo_postgis_adapter)
safe_number_provider_base_url = os.getenv("SAFE_NUMBER_PROVIDER_BASE_URL")
if safe_number_provider_base_url:
    _safe_number_repository = SafeNumberRepository(
        gateway=ProviderSafeNumberGateway(
            SafeNumberProviderClient(base_url=safe_number_provider_base_url, timeout_seconds=5.0),
        )
    )
else:
    _safe_number_repository = SafeNumberRepository()
_safe_number_service = SafeNumberService(_safe_number_repository)
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


def get_safe_number_service() -> SafeNumberService:
    return _safe_number_service


def get_geo_service() -> GeoService:
    return _geo_service
