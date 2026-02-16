# Search Service (`apps/search-service`)

검색 인덱스 전용 서비스입니다.

## 역할
- 시설 검색 질의 처리
- 내부 인덱싱 업서트 수신
- 검색 최적화 모델/스토어 분리

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `GET /v1/search/facilities`
- `POST /internal/search/index`

## 코드 구조
- `src/search_service/app.py`: API 진입점
- `src/search_service/store.py`: SQLAlchemy ORM 저장소
- `src/search_service/models.py`: ORM 모델
- `src/search_service/schemas.py`: 요청 스키마
- `alembic/`: DB 마이그레이션
