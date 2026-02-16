# Auth Service (`apps/auth-service`)

인증/토큰 발급 전담 서비스입니다.

## 역할
- 로그인, 토큰 재발급, 로그아웃
- JWT 발급/검증
- revoked token 저장소(기본 Redis, 실패 시 fallback)
- 로그인 rate limit

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`

## 코드 구조
- `src/auth_service/app.py`: FastAPI 앱 및 인증 흐름
- `src/auth_service/schemas.py`: 요청/응답 스키마
- `src/auth_service/rate_limit.py`: 로그인 제한
- `alembic/`: DB 마이그레이션(필요 시)
