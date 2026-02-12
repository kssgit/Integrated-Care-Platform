from __future__ import annotations

import pytest

from data_pipeline.jobs.__main__ import _required_env


def test_required_env_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("FACILITY_PROVIDER_BASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        _required_env("FACILITY_PROVIDER_BASE_URL")

