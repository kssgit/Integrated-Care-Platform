# User Service (`apps/user-service`)

사용자/선호도/감사로그 도메인 서비스입니다.

## 역할
- 사용자 CRUD
- 사용자 선호도 조회/저장
- 접근 권한(Role) 검증
- 민감 데이터(전화번호) 암호화 저장
- 사용자 조회 감사로그 기록

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `POST /v1/users`
- `GET|PUT|DELETE /v1/users/{user_id}`
- `GET|PUT /v1/users/{user_id}/preferences`
- `GET /internal/snapshot` (관리자)

## 코드 구조
- `src/user_service/app.py`: 인증/인가 + API 핸들러
- `src/user_service/store.py`: SQLAlchemy ORM 기반 저장소
- `src/user_service/models.py`: ORM 모델
- `src/user_service/schemas.py`: API 스키마
- `alembic/`: DB 마이그레이션
