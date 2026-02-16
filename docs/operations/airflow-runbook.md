# Airflow Runbook

This document explains how to connect Apache Airflow to the data pipeline package.

## Scope

1. Keep ETL logic in `packages/data-pipeline/src/data_pipeline/core`
2. Keep orchestration logic in `packages/data-pipeline/src/data_pipeline/orchestration`
3. Keep DAG definitions in `packages/data-pipeline/dags`

## Install Airflow (Optional)

Airflow is optional in local development. Install only when orchestration is required.

```bash
source .venv/bin/activate
pip install "apache-airflow>=2.9,<3.0"
```

## DAG Entry

Use:

`packages/data-pipeline/dags/daily_sync_dag.py`

The current DAG uses placeholder extractor/store components and must be replaced with production implementations.

## Wiring Rule

1. DAG should call `create_daily_sync_dag(...)` from `data_pipeline.orchestration.airflow_adapter`
2. DAG should provide extractor/store factories through DI
3. Core ETL should not import Airflow directly

## Validation

Run tests:

```bash
./scripts/run-tests.sh
```
