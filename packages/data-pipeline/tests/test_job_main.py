from __future__ import annotations

import pytest

from data_pipeline.jobs.__main__ import _build_store, _required_env
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
    store = _build_store("postgres")
    assert isinstance(store, PostgresFacilityStore)
