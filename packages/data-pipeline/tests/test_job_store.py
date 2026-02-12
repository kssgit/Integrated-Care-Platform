from __future__ import annotations

import json
from datetime import datetime

import pytest

from data_pipeline.core.models import FacilityRecord
from data_pipeline.jobs.store import JsonlFacilityStore


@pytest.mark.asyncio
async def test_jsonl_store_upserts_latest_record(tmp_path) -> None:
    store = JsonlFacilityStore(str(tmp_path / "facilities.jsonl"))
    old = FacilityRecord(
        source_id="A1",
        name="Center",
        address="Seoul",
        district_code="11110",
        lat=37.0,
        lng=127.0,
        source_updated_at=datetime(2026, 1, 1),
    )
    new = FacilityRecord(
        source_id="A1",
        name="Center New",
        address="Seoul",
        district_code="11110",
        lat=37.0,
        lng=127.0,
        source_updated_at=datetime(2026, 1, 2),
    )

    await store.upsert_many([old])
    await store.upsert_many([new])
    lines = (tmp_path / "facilities.jsonl").read_text(encoding="utf-8").splitlines()
    saved = [json.loads(line) for line in lines]

    assert len(saved) == 1
    assert saved[0]["name"] == "Center New"
