# API Service (`apps/api`)

통합 진입점(BFF) 서비스입니다.

## 역할
- 외부 클라이언트 단일 진입점 제공
- `auth-service`, `user-service`, `facility-service`, `search-service` 게이트웨이 라우팅
- 지리/안전성(geo, trust-safety) API 노출
- 내부 이벤트 수신 및 공통 응답 스키마/오류 처리
- `/metrics` 제공 및 API 관측(미들웨어)

## 주요 엔드포인트
- `GET /healthz`, `GET /readyz`, `GET /metrics`
- `POST /v1/auth/*` (auth 게이트웨이)
- `GET|POST|PUT|DELETE /v1/users/*` (user 게이트웨이)
- `GET /v1/facilities*` (facility 게이트웨이)
- `GET /v1/search/facilities` (search 게이트웨이)
- `GET /v1/geo/*`, `GET /v1/trust-safety/*`
- `POST /internal/events/*`

## 코드 구조
- `src/api/app.py`: 앱 조립(라우터, 예외처리, metrics)
- `src/api/routers/`: 도메인별 라우터
- `src/api/clients/`: 내부 서비스 호출 클라이언트
- `src/api/dependencies.py`: 캐시/클라이언트 의존성 주입
- `src/api/event_*.py`: Kafka consumer/DLQ/parking monitor 워커
