from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from data_pipeline.core.pipeline import Extractor, FacilityStore
from data_pipeline.jobs.daily_sync import run_daily_sync

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False
    DAG = Any  # type: ignore[misc,assignment]
    PythonOperator = Any  # type: ignore[misc,assignment]


def build_daily_sync_callable(
    extractor_factory: Callable[[], Extractor[dict]],
    store_factory: Callable[[], FacilityStore],
) -> Callable[[], int]:
    def _run() -> int:
        extractor = extractor_factory()
        store = store_factory()
        return asyncio.run(run_daily_sync(extractor, store))

    return _run


def create_daily_sync_dag(
    dag_id: str,
    extractor_factory: Callable[[], Extractor[dict]],
    store_factory: Callable[[], FacilityStore],
    schedule: str = "@daily",
    start_date: datetime | None = None,
) -> Any:
    if not AIRFLOW_AVAILABLE:
        raise RuntimeError("apache-airflow is not installed")

    dag = DAG(
        dag_id=dag_id,
        schedule=schedule,
        start_date=start_date or datetime(2026, 1, 1),
        catchup=False,
        tags=["data-pipeline", "etl"],
    )
    PythonOperator(
        task_id="daily_sync",
        python_callable=build_daily_sync_callable(extractor_factory, store_factory),
        dag=dag,
    )
    return dag

