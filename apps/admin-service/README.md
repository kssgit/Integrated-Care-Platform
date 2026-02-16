# Admin Service (`apps/admin-service`)

운영 전용 API 서비스입니다.

## 역할
- 시설 데이터 수동 보정
- 파이프라인 실행/재실행/상태 조회 (Airflow 연동)
- 운영 감사 로그 조회

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `POST /v1/admin/facilities/{facility_id}/patch`
- `GET /v1/admin/facilities/{facility_id}/audit`
- `POST /v1/admin/pipeline/runs`
- `GET /v1/admin/pipeline/runs/{dag_run_id}`
- `POST /v1/admin/pipeline/runs/{dag_run_id}/retry`
- `GET /v1/admin/pipeline/runs`

## 인증
- 기존 JWT `admin` role 필요

## 환경변수
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `AIRFLOW_API_BASE_URL`
- `AIRFLOW_API_USERNAME`
- `AIRFLOW_API_PASSWORD`
- `AIRFLOW_DAG_ID` (기본: `seoul_care_plus_daily_sync`)

## DB Migration
- `alembic -c alembic.ini upgrade head`
- 스키마/테이블 생성은 Alembic으로 관리하며, 런타임 auto-create는 사용하지 않습니다.
