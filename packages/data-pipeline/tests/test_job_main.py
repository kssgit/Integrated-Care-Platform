from __future__ import annotations

import pytest

from data_pipeline.jobs.__main__ import _build_store, _provider_endpoint_path, _required_env
from data_pipeline.jobs.postgres_store import PostgresFacilityStore
from data_pipeline.jobs.store import JsonlFacilityStore


def test_required_env_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("FACILITY_PROVIDER_BASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        _required_env("FACILITY_PROVIDER_BASE_URL")


def test_build_store_defaults_to_jsonl() -> None:
    store = _build_store("jsonl")
    assert isinstance(store, JsonlFacilityStore)


def test_build_store_requires_database_url_for_postgres(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        _build_store("postgres")


def test_build_store_uses_postgres_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("PIPELINE_DB_BATCH_SIZE", "2000")
    store = _build_store("postgres")
    assert isinstance(store, PostgresFacilityStore)
    assert store._batch_size == 2000


def test_provider_endpoint_path_returns_seoul_default_path() -> None:
    assert _provider_endpoint_path("seoul_open_data") == "/facilities"


def test_provider_endpoint_path_returns_seoul_district_path() -> None:
    assert _provider_endpoint_path("seoul_district_open_data") == "/seoul/district/facilities"


def test_provider_endpoint_path_returns_mohw_path() -> None:
    assert _provider_endpoint_path("mohw_open_data") == "/mohw/facilities"


def test_provider_endpoint_path_raises_for_unsupported_provider() -> None:
    with pytest.raises(RuntimeError):
        _provider_endpoint_path("unknown_provider")
