from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageDuration:
    stage: str
    duration_ms: float


class InMemoryPipelineMetricsCollector:
    def __init__(self) -> None:
        self.stage_durations: list[StageDuration] = []
        self.external_api_error_count = 0
        self.processed_records = 0
        self.quality_rejected_records = 0

    def observe_stage_duration(self, stage: str, duration_ms: float) -> None:
        self.stage_durations.append(StageDuration(stage=stage, duration_ms=duration_ms))

    def increment_external_api_error(self) -> None:
        self.external_api_error_count += 1

    def add_processed_records(self, count: int) -> None:
        self.processed_records += count

    def add_quality_rejected_records(self, count: int) -> None:
        self.quality_rejected_records += count
