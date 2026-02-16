from __future__ import annotations

import asyncio
import os

from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.core.quality import FacilityQualityGate
from data_pipeline.jobs.daily_sync import run_daily_sync
from data_pipeline.jobs.events import publish_etl_completed_event
from data_pipeline.jobs.extractor import ProviderFacilityExtractor
from data_pipeline.jobs.postgres_store import PostgresFacilityStore
from data_pipeline.jobs.publishing_store import PublishingFacilityStore
from data_pipeline.jobs.store import JsonlFacilityStore
from data_pipeline.messaging.kafka_broker import KafkaMessageBroker
from data_pipeline.monitoring.state import pipeline_metrics

_PROVIDER_ENDPOINT_PATHS: dict[str, str] = {
    "seoul_open_data": "/facilities",
    "seoul_district_open_data": "/seoul/district/facilities",
    "gyeonggi_open_data": "/gyeonggi/facilities",
    "national_open_data": "/national/facilities",
    "mohw_open_data": "/mohw/facilities",
}


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def _build_store(backend: str) -> FacilityStore:
    if backend == "postgres":
        dsn = _required_env("DATABASE_URL")
        batch_size = int(os.getenv("PIPELINE_DB_BATCH_SIZE", "1000"))
        return PostgresFacilityStore(dsn=dsn, batch_size=batch_size)
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


def _maybe_build_event_broker() -> KafkaMessageBroker | None:
    enabled = os.getenv("PIPELINE_API_EVENT_PUBLISH_ENABLED", "false").lower() == "true"
    if not enabled:
        return None
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    return KafkaMessageBroker(bootstrap_servers=bootstrap)


def _provider_endpoint_path(provider: str) -> str:
    endpoint = _PROVIDER_ENDPOINT_PATHS.get(provider)
    if endpoint:
        return endpoint
    supported = ", ".join(sorted(_PROVIDER_ENDPOINT_PATHS.keys()))
    raise RuntimeError(f"unsupported PIPELINE_PROVIDER_NAME '{provider}', supported: {supported}")


def _parse_positive_int(name: str, default: str) -> int:
    value = int(os.getenv(name, default))
    if value <= 0:
        raise RuntimeError(f"{name} must be > 0")
    return value


def _parse_non_negative_float(name: str, default: str) -> float:
    value = float(os.getenv(name, default))
    if value < 0:
        raise RuntimeError(f"{name} must be >= 0")
    return value


def main() -> None:
    base_url = _required_env("FACILITY_PROVIDER_BASE_URL")
    provider = os.getenv("PIPELINE_PROVIDER_NAME", "seoul_open_data")
    backend = os.getenv("PIPELINE_STORE_BACKEND", "jsonl").lower()
    page_size = _parse_positive_int("PIPELINE_PAGE_SIZE", "200")
    start_page = _parse_positive_int("PIPELINE_START_PAGE", "1")
    end_page = _parse_positive_int("PIPELINE_END_PAGE", "1")
    if end_page < start_page:
        raise RuntimeError("PIPELINE_END_PAGE must be >= PIPELINE_START_PAGE")
    connect_timeout_seconds = _parse_non_negative_float("PIPELINE_HTTP_CONNECT_TIMEOUT_SECONDS", "2.0")
    read_timeout_seconds = _parse_non_negative_float("PIPELINE_HTTP_READ_TIMEOUT_SECONDS", "5.0")
    max_retries = _parse_positive_int("PIPELINE_PROVIDER_MAX_RETRIES", "3")
    retry_base_delay_seconds = _parse_non_negative_float("PIPELINE_PROVIDER_RETRY_BASE_DELAY_SECONDS", "0.1")
    quality_max_reject_ratio = float(os.getenv("PIPELINE_QUALITY_MAX_REJECT_RATIO", "0.2"))
    quality_reject_sample_size = _parse_positive_int("PIPELINE_QUALITY_REJECT_SAMPLE_SIZE", "5")

    extractor = ProviderFacilityExtractor(
        base_url=base_url,
        provider_name=provider,
        endpoint_path=_provider_endpoint_path(provider),
        page_size=page_size,
        start_page=start_page,
        end_page=end_page,
        connect_timeout_seconds=connect_timeout_seconds,
        read_timeout_seconds=read_timeout_seconds,
        max_retries=max_retries,
        retry_base_delay_seconds=retry_base_delay_seconds,
        metrics=pipeline_metrics,
    )
    store = _build_store(backend=backend)
    store = _maybe_wrap_with_publisher(store)
    event_broker = _maybe_build_event_broker()
    quality_gate = FacilityQualityGate(
        max_reject_ratio=quality_max_reject_ratio,
        reject_sample_size=quality_reject_sample_size,
    )
    saved_count = asyncio.run(run_daily_sync(extractor=extractor, store=store, quality_gate=quality_gate))
    if event_broker:
        asyncio.run(
            publish_etl_completed_event(
                broker=event_broker,
                provider=provider,
                saved_count=saved_count,
            )
        )


if __name__ == "__main__":
    main()
