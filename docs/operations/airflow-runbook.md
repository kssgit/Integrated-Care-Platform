# Airflow Runbook

## Scope
- Airflow는 `packages/data-pipeline/dags/daily_sync_dag.py`를 실행한다.
- DAG 입력 계약은 `provider_name`, `start_page`, `end_page`, `dry_run` 이다.
- 운영 제어는 `apps/admin-service`의 Airflow REST client를 통해 수행한다.

## Required Config
- `AIRFLOW_API_BASE_URL`
- `AIRFLOW_API_USERNAME`
- `AIRFLOW_API_PASSWORD`
- `AIRFLOW_DAG_ID` (default: `seoul_care_plus_daily_sync`)
- `AIRFLOW_API_TIMEOUT_SECONDS` (default: `5.0`)
- `AIRFLOW_API_MAX_RETRIES` (default: `3`)
- `AIRFLOW_API_RETRY_BASE_DELAY_SECONDS` (default: `0.2`)

## Pipeline Runtime Config
- `PIPELINE_PROVIDER_NAME`
- `PIPELINE_START_PAGE`
- `PIPELINE_END_PAGE`
- `PIPELINE_PAGE_SIZE`
- `PIPELINE_HTTP_CONNECT_TIMEOUT_SECONDS`
- `PIPELINE_HTTP_READ_TIMEOUT_SECONDS`
- `PIPELINE_PROVIDER_MAX_RETRIES`
- `PIPELINE_PROVIDER_RETRY_BASE_DELAY_SECONDS`
- `PIPELINE_QUALITY_MAX_REJECT_RATIO`
- `PIPELINE_QUALITY_REJECT_SAMPLE_SIZE`

## DAG Parameter Contract
1. `provider_name`
- enum: `seoul_open_data`, `seoul_district_open_data`, `gyeonggi_open_data`, `national_open_data`, `mohw_open_data`

2. `start_page`, `end_page`
- `>= 1`
- `end_page >= start_page`

3. `dry_run`
- `true`이면 추출/정규화만 수행하고 저장은 생략

검증 실패 시 task는 즉시 실패한다.

## Admin API Integration
1. Trigger
```bash
curl -u "$AIRFLOW_API_USERNAME:$AIRFLOW_API_PASSWORD" \
  -H 'Content-Type: application/json' \
  -X POST "$AIRFLOW_API_BASE_URL/api/v1/dags/$AIRFLOW_DAG_ID/dagRuns" \
  -d '{"dag_run_id":"manual-run-1","conf":{"provider_name":"seoul_open_data","start_page":1,"end_page":1,"dry_run":false}}'
```

2. Status
```bash
curl -u "$AIRFLOW_API_USERNAME:$AIRFLOW_API_PASSWORD" \
  "$AIRFLOW_API_BASE_URL/api/v1/dags/$AIRFLOW_DAG_ID/dagRuns/manual-run-1"
```

## Error Handling Standard
- timeout: `AIRFLOW_TIMEOUT` (504)
- unauthorized: `AIRFLOW_UNAUTHORIZED` (502)
- not found: `AIRFLOW_NOT_FOUND` (404)
- bad request: `AIRFLOW_BAD_REQUEST` (400)
- 429/5xx: `AIRFLOW_UPSTREAM_ERROR` (502, retry/backoff)
- 기타 네트워크 오류: `AIRFLOW_UNAVAILABLE` (502)

## Smoke Checklist (Dev)
- [ ] Airflow webserver NodePort 접속 가능
- [ ] `POST /v1/admin/pipeline/runs` 1회 성공
- [ ] `GET /v1/admin/pipeline/runs/{dag_run_id}` 상태 추적 가능
- [ ] provider 1페이지 수집 성공
- [ ] `/metrics`에서 `pipeline_run_total`, `pipeline_reject_ratio` 확인

## Rollback
1. 문제 이미지 확인: `kubectl -n integrated-care get pods -o wide`
2. 이전 릴리스 확인: `helm -n integrated-care history integrated-care`
3. 롤백 실행: `helm -n integrated-care rollback integrated-care <REVISION>`
4. 실패 원인 기록: Airflow task log + admin-service log + pipeline metrics
