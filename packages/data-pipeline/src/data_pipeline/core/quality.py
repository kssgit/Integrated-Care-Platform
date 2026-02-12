from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.models import FacilityRecord


@dataclass(frozen=True)
class QualityResult:
    accepted: list[FacilityRecord]
    rejected_count: int


class FacilityQualityGate:
    def __init__(self, max_reject_ratio: float = 0.2) -> None:
        if max_reject_ratio < 0 or max_reject_ratio > 1:
            raise ValueError("max_reject_ratio must be between 0 and 1")
        self._max_reject_ratio = max_reject_ratio

    def filter_or_raise(self, records: list[FacilityRecord]) -> QualityResult:
        if not records:
            return QualityResult(accepted=[], rejected_count=0)
        accepted = [record for record in records if self._is_valid(record)]
        rejected = len(records) - len(accepted)
        reject_ratio = rejected / len(records)
        if reject_ratio > self._max_reject_ratio:
            raise ValidationError(
                f"quality threshold exceeded: rejected={rejected}, total={len(records)}"
            )
        return QualityResult(accepted=accepted, rejected_count=rejected)

    def _is_valid(self, record: FacilityRecord) -> bool:
        if not record.name.strip() or not record.address.strip() or not record.district_code.strip():
            return False
        if not (-90 <= record.lat <= 90):
            return False
        if not (-180 <= record.lng <= 180):
            return False
        return isinstance(record.source_updated_at, datetime)
