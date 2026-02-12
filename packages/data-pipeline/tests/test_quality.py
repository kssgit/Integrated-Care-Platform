from __future__ import annotations

from datetime import datetime

import pytest

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.quality import FacilityQualityGate


def _record(lat: float = 37.5, lng: float = 126.9, name: str = "Center") -> FacilityRecord:
    return FacilityRecord(
        source_id="A1",
        name=name,
        address="Seoul",
        district_code="11110",
        lat=lat,
        lng=lng,
        source_updated_at=datetime(2026, 1, 1),
    )


def test_quality_gate_filters_invalid_records_under_threshold() -> None:
    gate = FacilityQualityGate(max_reject_ratio=0.5)
    result = gate.filter_or_raise([_record(), _record(lat=120.0)])

    assert len(result.accepted) == 1
    assert result.rejected_count == 1


def test_quality_gate_raises_when_reject_ratio_exceeds_threshold() -> None:
    gate = FacilityQualityGate(max_reject_ratio=0.2)

    with pytest.raises(ValidationError):
        gate.filter_or_raise([_record(lat=120.0), _record(lng=200.0), _record()])
