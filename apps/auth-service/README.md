# Auth Service (`apps/auth-service`)

인증/토큰 발급 전담 서비스입니다.

## 역할
- 회원가입, 로그인, 토큰 재발급, 로그아웃
- 가입/SSO 시 user-service 사용자 bootstrap 연동
- JWT 발급/검증
- revoked token 저장소(기본 Redis, 실패 시 fallback)
- 로그인 rate limit
- Google/Naver SSO 로그인
- 계정 연결 정책(동일 이메일 기존 로컬 계정 자동 링크)

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`
- `POST /v1/auth/login`
- `POST /v1/auth/signup`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `GET /v1/auth/sso/{provider}/authorize`
- `POST /v1/auth/sso/{provider}/callback`

## 참고
- `DATABASE_URL`이 PostgreSQL이면 SQLAlchemy ORM + Alembic 스키마(`auth.users`, `auth.sso_identities`)를 사용합니다.
- `DATABASE_URL` 미지정 시 인메모리 fallback으로 동작합니다.
- SSO 환경변수:
  - `AUTH_SSO_PROVIDERS` (예: `google,naver`)
  - `AUTH_SSO_<PROVIDER>_CLIENT_ID`
  - `AUTH_SSO_<PROVIDER>_CLIENT_SECRET`
  - `AUTH_SSO_<PROVIDER>_AUTHORIZE_URL`
  - `AUTH_SSO_<PROVIDER>_TOKEN_URL`
  - `AUTH_SSO_<PROVIDER>_USERINFO_URL`
  - `AUTH_SSO_<PROVIDER>_REDIRECT_URI` (callback 요청 본문에 `redirect_uri`가 없을 때 사용)
- 계정 연결 규칙:
  - 같은 `provider + provider_subject`가 존재하면 기존 계정 로그인
  - 없고, SSO 이메일이 기존 로컬 계정과 일치하면 기존 계정에 연결
  - 둘 다 없으면 신규 SSO 계정 생성
- user-service bootstrap 연동:
  - `USER_SERVICE_BASE_URL`
  - `INTERNAL_EVENT_HMAC_SECRET` (user-service 내부 bootstrap 토큰과 동일해야 함)

## 코드 구조
- `src/auth_service/app.py`: FastAPI 앱 및 인증 흐름
- `src/auth_service/schemas.py`: 요청/응답 스키마
- `src/auth_service/rate_limit.py`: 로그인 제한
- `alembic/`: DB 마이그레이션(필요 시)
