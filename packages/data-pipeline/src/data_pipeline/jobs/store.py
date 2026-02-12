from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore


def _serialize(record: FacilityRecord) -> dict:
    payload = asdict(record)
    payload["source_updated_at"] = record.source_updated_at.isoformat()
    return payload


def _deserialize(payload: dict) -> FacilityRecord:
    return FacilityRecord(
        source_id=str(payload["source_id"]),
        name=str(payload["name"]),
        address=str(payload["address"]),
        district_code=str(payload["district_code"]),
        lat=float(payload["lat"]),
        lng=float(payload["lng"]),
        source_updated_at=datetime.fromisoformat(str(payload["source_updated_at"])),
    )


class JsonlFacilityStore(FacilityStore):
    def __init__(self, file_path: str) -> None:
        self._file = Path(file_path)

    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        latest = self._read_existing()
        for record in records:
            current = latest.get(record.source_id)
            if current is None or record.source_updated_at > current.source_updated_at:
                latest[record.source_id] = record
        self._write_all(latest)
        return len(records)

    def _read_existing(self) -> dict[str, FacilityRecord]:
        if not self._file.exists():
            return {}
        latest: dict[str, FacilityRecord] = {}
        for line in self._file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = _deserialize(json.loads(line))
            latest[record.source_id] = record
        return latest

    def _write_all(self, latest: dict[str, FacilityRecord]) -> None:
        lines = [json.dumps(_serialize(record), ensure_ascii=True) for record in latest.values()]
        self._file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

