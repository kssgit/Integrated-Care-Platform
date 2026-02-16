from __future__ import annotations

import asyncio
from datetime import datetime
import os
from typing import Any

from data_pipeline.core.quality import FacilityQualityGate
from data_pipeline.jobs.daily_sync import run_daily_sync
from data_pipeline.jobs.extractor import ProviderFacilityExtractor
from data_pipeline.jobs.postgres_store import PostgresFacilityStore
from data_pipeline.jobs.store import JsonlFacilityStore
from data_pipeline.orchestration.airflow_adapter import AIRFLOW_AVAILABLE, DAG, PythonOperator

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


def _build_store(backend: str):
    if backend == "postgres":
        dsn = _required_env("DATABASE_URL")
        batch_size = int(os.getenv("PIPELINE_DB_BATCH_SIZE", "1000"))
        return PostgresFacilityStore(dsn=dsn, batch_size=batch_size)
    output_path = os.getenv("PIPELINE_OUTPUT_FILE", "runtime/facilities.jsonl")
    return JsonlFacilityStore(file_path=output_path)


def _provider_endpoint_path(provider: str) -> str:
    endpoint = _PROVIDER_ENDPOINT_PATHS.get(provider)
    if endpoint:
        return endpoint
    supported = ", ".join(sorted(_PROVIDER_ENDPOINT_PATHS.keys()))
    raise RuntimeError(f"unsupported provider '{provider}', supported: {supported}")


def _resolve_job_params(conf: dict[str, Any]) -> dict[str, Any]:
    provider_name = str(conf.get("provider_name") or os.getenv("PIPELINE_PROVIDER_NAME", "seoul_open_data"))
    start_page = int(conf.get("start_page") or os.getenv("PIPELINE_START_PAGE", "1"))
    end_page = int(conf.get("end_page") or os.getenv("PIPELINE_END_PAGE", "1"))
    dry_run = bool(conf.get("dry_run", False))
    page_size = int(os.getenv("PIPELINE_PAGE_SIZE", "200"))
    backend = os.getenv("PIPELINE_STORE_BACKEND", "jsonl").lower()
    quality_max_reject_ratio = float(os.getenv("PIPELINE_QUALITY_MAX_REJECT_RATIO", "0.2"))
    base_url = _required_env("FACILITY_PROVIDER_BASE_URL")
    return {
        "provider_name": provider_name,
        "start_page": start_page,
        "end_page": end_page,
        "dry_run": dry_run,
        "page_size": page_size,
        "backend": backend,
        "quality_max_reject_ratio": quality_max_reject_ratio,
        "base_url": base_url,
    }


def _run_daily_sync_with_conf(**context: Any) -> int:
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run and isinstance(dag_run.conf, dict) else {}
    params = _resolve_job_params(conf=conf)

    extractor = ProviderFacilityExtractor(
        base_url=params["base_url"],
        endpoint_path=_provider_endpoint_path(params["provider_name"]),
        page_size=params["page_size"],
        start_page=params["start_page"],
        end_page=params["end_page"],
    )
    quality_gate = FacilityQualityGate(max_reject_ratio=params["quality_max_reject_ratio"])

    if params["dry_run"]:
        async def _dry_run() -> int:
            records = await extractor.extract()
            return len(records)

        return asyncio.run(_dry_run())

    store = _build_store(backend=params["backend"])
    return asyncio.run(run_daily_sync(extractor=extractor, store=store, quality_gate=quality_gate))


if AIRFLOW_AVAILABLE:
    dag = DAG(
        dag_id="seoul_care_plus_daily_sync",
        schedule="@daily",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["data-pipeline", "etl"],
    )
    PythonOperator(
        task_id="daily_sync",
        python_callable=_run_daily_sync_with_conf,
        dag=dag,
    )
else:
    dag = None
