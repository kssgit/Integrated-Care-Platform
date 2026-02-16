# packages/devkit

서비스 간 중복되는 인프라 런타임 코드를 모은 공통 패키지.

## 포함 모듈
- `devkit.config`: 환경 변수 기반 서비스 설정 로더
- `devkit.db`: PostgreSQL DSN 정규화, SQLAlchemy 스키마/세션/재연결 매니저
- `devkit.redis`: async Redis 연결 매니저(health check, 재연결, backoff)
- `devkit.kafka`: async Kafka consumer/producer 연결 및 재연결/backoff 유틸
- `devkit.observability`: OpenTelemetry 기본 초기화

## 원칙
- 서비스별 도메인 로직은 `apps/*`에서 유지
- 인프라 연결/초기화는 `devkit`으로 통합
