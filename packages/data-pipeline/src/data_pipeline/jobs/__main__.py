from __future__ import annotations

import asyncio
import os

from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.jobs.daily_sync import run_daily_sync
from data_pipeline.jobs.extractor import ProviderFacilityExtractor
from data_pipeline.jobs.postgres_store import PostgresFacilityStore
from data_pipeline.jobs.publishing_store import PublishingFacilityStore
from data_pipeline.jobs.store import JsonlFacilityStore
from data_pipeline.messaging.kafka_broker import KafkaMessageBroker


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def _build_store(backend: str) -> FacilityStore:
    if backend == "postgres":
        dsn = _required_env("DATABASE_URL")
        return PostgresFacilityStore(dsn=dsn)
    output_path = os.getenv("PIPELINE_OUTPUT_FILE", "runtime/facilities.jsonl")
    return JsonlFacilityStore(file_path=output_path)


def _maybe_wrap_with_publisher(store: FacilityStore) -> FacilityStore:
    enabled = os.getenv("PIPELINE_KAFKA_PUBLISH_ENABLED", "false").lower() == "true"
    if not enabled:
        return store
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    provider = os.getenv("PIPELINE_PROVIDER_NAME", "seoul_open_data")
    broker = KafkaMessageBroker(bootstrap_servers=bootstrap)
    return PublishingFacilityStore(delegate=store, broker=broker, provider=provider)


def main() -> None:
    base_url = _required_env("FACILITY_PROVIDER_BASE_URL")
    backend = os.getenv("PIPELINE_STORE_BACKEND", "jsonl").lower()
    page_size = int(os.getenv("PIPELINE_PAGE_SIZE", "200"))
    start_page = int(os.getenv("PIPELINE_START_PAGE", "1"))
    end_page = int(os.getenv("PIPELINE_END_PAGE", "1"))

    extractor = ProviderFacilityExtractor(
        base_url=base_url,
        page_size=page_size,
        start_page=start_page,
        end_page=end_page,
    )
    store = _build_store(backend=backend)
    store = _maybe_wrap_with_publisher(store)
    asyncio.run(run_daily_sync(extractor=extractor, store=store))


if __name__ == "__main__":
    main()
