# Facility Service (`apps/facility-service`)

시설 데이터 원천 저장/조회 서비스입니다.

## 역할
- 시설 목록/상세/검색 조회
- ETL 파이프라인 업서트 수신(`internal`)
- 시설 메타데이터 저장소 역할

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `GET /v1/facilities`
- `GET /v1/facilities/search`
- `GET /v1/facilities/{facility_id}`
- `POST /internal/facilities/upsert`

## 코드 구조
- `src/facility_service/app.py`: API 진입점
- `src/facility_service/store.py`: SQLAlchemy ORM 저장소
- `src/facility_service/models.py`: ORM 모델
- `src/facility_service/schemas.py`: 요청 스키마
- `alembic/`: DB 마이그레이션
