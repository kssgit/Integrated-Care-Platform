from __future__ import annotations

from data_pipeline.core.pipeline import ETLPipeline, Extractor, FacilityStore
from data_pipeline.monitoring.state import pipeline_metrics


async def run_daily_sync(extractor: Extractor[dict], store: FacilityStore) -> int:
    pipeline = ETLPipeline(extractor=extractor, store=store, metrics=pipeline_metrics)
    return await pipeline.run()

