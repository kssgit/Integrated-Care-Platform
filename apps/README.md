# Apps Structure

`apps`는 서비스별 실행 단위를 분리한 폴더입니다.

## 서비스 맵
- `apps/api`: 외부 진입 BFF
- `apps/auth-service`: 인증/토큰
- `apps/user-service`: 사용자/선호도
- `apps/facility-service`: 시설 원천 데이터
- `apps/search-service`: 검색 인덱스
- `apps/admin-service`: 운영 API (시설 보정/파이프라인 제어)
- `apps/admin`: 운영 콘솔 문서/자산(선택)

## 공통 규칙
- 서비스 도메인 로직: `apps/*`
- 보안/계약 공통: `packages/shared`
- 인프라 런타임(DB/Redis/Kafka/설정/관측): `packages/devkit`
