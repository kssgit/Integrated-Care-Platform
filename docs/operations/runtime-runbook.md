# Runtime Runbook

This runbook defines the standard local runtime commands for the platform.

## Prerequisites

1. Python 3.12 installed
2. Project virtual environment exists at `.venv`
3. Dependencies installed with `pip install -r requirements.txt`
4. Commands are executed in Git Bash

## Start API Server

```bash
./scripts/run-api.sh
```

Default bind:

1. host: `0.0.0.0`
2. port: `8000`

Override:

```bash
API_HOST=0.0.0.0 API_PORT=8010 ./scripts/run-api.sh
```

## Start Data Pipeline Monitoring Server

```bash
./scripts/run-data-pipeline-monitoring.sh
```

Default bind:

1. host: `0.0.0.0`
2. port: `8001`

Override:

```bash
PIPELINE_MONITORING_HOST=0.0.0.0 PIPELINE_MONITORING_PORT=8011 ./scripts/run-data-pipeline-monitoring.sh
```

## Run Data Pipeline Job (One-shot)

```bash
FACILITY_PROVIDER_BASE_URL=https://provider.example.com \
PIPELINE_START_PAGE=1 PIPELINE_END_PAGE=1 \
./scripts/run-data-pipeline-job.sh
```

PostgreSQL + Kafka example:

```bash
FACILITY_PROVIDER_BASE_URL=https://provider.example.com \
PIPELINE_STORE_BACKEND=postgres \
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/integrated_care \
PIPELINE_KAFKA_PUBLISH_ENABLED=true \
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
./scripts/run-data-pipeline-job.sh
```

## Run Tests

```bash
./scripts/run-tests.sh
```

## Metrics Endpoints

1. API metrics: `http://localhost:8000/metrics`
2. API health: `http://localhost:8000/healthz`
3. Pipeline metrics: `http://localhost:8001/metrics`
4. Pipeline health: `http://localhost:8001/healthz`

## Orchestration

1. Airflow integration guide: `docs/operations/airflow-runbook.md`
2. Airflow DAG template: `packages/data-pipeline/dags/daily_sync_dag.py`
3. Kubernetes/AKS deployment guide: `docs/operations/k8s-aks-runbook.md`
4. Helm chart: `infra/helm/integrated-care`
