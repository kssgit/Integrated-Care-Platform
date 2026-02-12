from __future__ import annotations

from data_pipeline.core.pipeline import ETLPipeline, Extractor, FacilityStore
from data_pipeline.core.quality import FacilityQualityGate
from data_pipeline.monitoring.state import pipeline_metrics


async def run_daily_sync(
    extractor: Extractor[dict],
    store: FacilityStore,
    quality_gate: FacilityQualityGate | None = None,
) -> int:
    pipeline = ETLPipeline(
        extractor=extractor,
        store=store,
        metrics=pipeline_metrics,
        quality_gate=quality_gate,
    )
    return await pipeline.run()
