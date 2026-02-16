from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


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
        self.pipeline_run_total: dict[tuple[str, str], int] = defaultdict(int)
        self.pipeline_records_total: dict[tuple[str, str], int] = defaultdict(int)
        self.pipeline_reject_ratio: dict[str, float] = {}
        self.pipeline_duration_seconds: dict[str, float] = {}
        self.pipeline_provider_http_errors_total: dict[tuple[str, str], int] = defaultdict(int)
        self._active_provider = "unknown"

    def observe_stage_duration(self, stage: str, duration_ms: float) -> None:
        self.stage_durations.append(StageDuration(stage=stage, duration_ms=duration_ms))

    def increment_external_api_error(self) -> None:
        self.external_api_error_count += 1

    def set_active_provider(self, provider: str) -> None:
        self._active_provider = provider or "unknown"

    def increment_run(self, status: str, provider: str | None = None) -> None:
        key = (provider or self._active_provider, status)
        self.pipeline_run_total[key] += 1

    def add_processed_records(self, count: int) -> None:
        self.processed_records += count
        self.add_records("accepted", count=count)

    def add_quality_rejected_records(self, count: int) -> None:
        self.quality_rejected_records += count
        self.add_records("rejected", count=count)

    def add_records(self, result: str, count: int, provider: str | None = None) -> None:
        if count <= 0:
            return
        key = (provider or self._active_provider, result)
        self.pipeline_records_total[key] += count

    def set_reject_ratio(self, ratio: float, provider: str | None = None) -> None:
        self.pipeline_reject_ratio[provider or self._active_provider] = ratio

    def observe_pipeline_duration(self, duration_seconds: float, provider: str | None = None) -> None:
        self.pipeline_duration_seconds[provider or self._active_provider] = duration_seconds

    def increment_provider_http_error(self, code: int | str, provider: str | None = None) -> None:
        key = (provider or self._active_provider, str(code))
        self.pipeline_provider_http_errors_total[key] += 1
