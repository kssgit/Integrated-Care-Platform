from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.models import FacilityRecord


@dataclass(frozen=True)
class QualityRejectedSample:
    source_id: str
    reason: str


@dataclass(frozen=True)
class QualityResult:
    accepted: list[FacilityRecord]
    rejected_count: int
    reject_ratio: float
    rejected_samples: list[QualityRejectedSample]


class FacilityQualityGate:
    def __init__(self, max_reject_ratio: float = 0.2, reject_sample_size: int = 5) -> None:
        if max_reject_ratio < 0 or max_reject_ratio > 1:
            raise ValueError("max_reject_ratio must be between 0 and 1")
        if reject_sample_size < 0:
            raise ValueError("reject_sample_size must be >= 0")
        self._max_reject_ratio = max_reject_ratio
        self._reject_sample_size = reject_sample_size

    def filter_or_raise(self, records: list[FacilityRecord]) -> QualityResult:
        if not records:
            return QualityResult(accepted=[], rejected_count=0, reject_ratio=0.0, rejected_samples=[])

        accepted: list[FacilityRecord] = []
        rejected_samples: list[QualityRejectedSample] = []
        for record in records:
            reject_reason = self._reject_reason(record)
            if reject_reason is None:
                accepted.append(record)
                continue
            if len(rejected_samples) < self._reject_sample_size:
                rejected_samples.append(
                    QualityRejectedSample(
                        source_id=record.source_id,
                        reason=reject_reason,
                    )
                )
        rejected = len(records) - len(accepted)
        reject_ratio = rejected / len(records)
        if reject_ratio > self._max_reject_ratio:
            sample_summary = ", ".join(f"{s.source_id}:{s.reason}" for s in rejected_samples)
            raise ValidationError(
                f"quality threshold exceeded: rejected={rejected}, total={len(records)}, samples={sample_summary}"
            )
        return QualityResult(
            accepted=accepted,
            rejected_count=rejected,
            reject_ratio=reject_ratio,
            rejected_samples=rejected_samples,
        )

    def _reject_reason(self, record: FacilityRecord) -> str | None:
        if not record.name.strip() or not record.address.strip() or not record.district_code.strip():
            return "missing_required_field"
        if not (-90 <= record.lat <= 90):
            return "invalid_lat_range"
        if not (-180 <= record.lng <= 180):
            return "invalid_lng_range"
        if not isinstance(record.source_updated_at, datetime):
            return "invalid_source_updated_at"
        return None
