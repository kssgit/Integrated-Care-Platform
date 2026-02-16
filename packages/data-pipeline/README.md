# Data Pipeline (`packages/data-pipeline`)

시설 데이터 ETL 파이프라인입니다.

## 역할
- 외부 공급자 API에서 시설 데이터 수집
- 정규화/품질검증/중복제거
- 저장소(JSONL/PostgreSQL) 적재
- Kafka 이벤트 발행(선택)
- 모니터링 메트릭(`/metrics`) 노출

## 구조
- `src/data_pipeline/core`: 파이프라인 코어(모델/품질/재시도)
- `src/data_pipeline/jobs`: 배치 실행 엔트리/스토어/이벤트 발행
- `src/data_pipeline/providers`: 공급자 어댑터(seoul/seoul_district/gyeonggi/national/mohw)
- `src/data_pipeline/orchestration/airflow_adapter.py`: Airflow DAG 어댑터
- `dags/daily_sync_dag.py`: Airflow DAG 정의(`dag_run.conf` 기반 파라미터 실행)

## 실행
- ETL 원샷: `python -m data_pipeline.jobs`
- 모니터링: `python -m data_pipeline.monitoring`

## Airflow
- Helm에서 `dependencies.airflow.enabled=true`로 Airflow 서브차트 활성화 가능
- DAG 연동은 `dags/`를 Airflow에 마운트(gitSync/volume)해야 실제 스케줄 실행 가능
- `dag_run.conf` 지원 파라미터:
  - `provider_name` (`seoul_open_data`, `seoul_district_open_data`, `gyeonggi_open_data`, `national_open_data`, `mohw_open_data`)
  - `start_page`, `end_page`, `dry_run`
