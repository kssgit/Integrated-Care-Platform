# 서울케어플러스(Seoul Care Plus) - MVP 구조 초안

서울형 통합 돌봄 중개 플랫폼 기획서(v2.0)를 기반으로, **서울 MVP를 빠르게 구현하고 수도권/전국으로 확장 가능한 모듈형 구조**를 제안합니다.

## 1) 제안 아키텍처 원칙

- **서울 우선 데이터 우위**: 서울 열린데이터광장 API를 1순위로 연동
- **도메인 분리**: 아동 돌봄 / 노인 돌봄 / 지역사회 복지 기능을 독립 모듈로 구성
- **신뢰/안전 우선**: 위치 기반 주민 인증, 리뷰 보호, robots.txt 준수 파이프라인 내재화
- **확장성**: `provider adapter` 패턴으로 경기/전국 API로 무중단 확장
- **관찰성**: 데이터 갱신 품질, API 장애, 매칭 성능, 안전 이벤트를 모니터링

## 2) 저장소 구조

```text
.
├── apps
│   ├── admin/                # 운영 콘솔(시설 심사, 리뷰 모더레이션, 광고 관리)
│   ├── api/                  # BFF/API 서버(검색, 매칭, 리뷰, 인증)
│   └── web/                  # 사용자 웹/모바일 웹
├── packages
│   ├── data-pipeline/        # 서울시/외부 API 수집-정제-적재(ETL)
│   ├── geo-engine/           # 안심 통학 지도, 골든타임 지수, 지오펜싱
│   ├── shared/               # 공통 타입, 유틸, 에러 규격, 로깅 스키마
│   └── trust-safety/         # 리뷰 인증, OCR 영수증, 안심번호, robots 준수
├── infra
│   ├── docker/               # 로컬/개발 컨테이너 설정
│   ├── k8s/                  # 배포 매니페스트(옵션)
│   └── terraform/            # 클라우드 IaC(옵션)
└── docs
    ├── architecture/         # 시스템/데이터/보안 아키텍처
    ├── product/              # PRD 및 기능 명세
    └── roadmap/              # 단계별 실행 계획
```

## 3) MVP 핵심 모듈 맵

- **Facility Search Domain**
  - 어린이집/요양시설/복지시설 통합 검색
  - 서울시 세부 속성(특수학급, 공실, 인증 등) 강조
- **Geo Intelligence Domain**
  - 스쿨존 CCTV + 사고 다발 구간 회피 경로
  - 시설→응급실 예상 이동시간 기반 골든타임 지수
- **Trust & Safety Domain**
  - 행정동 단위 지오펜싱 주민 인증
  - OCR 영수증 리뷰 인증
  - 050 안심번호 라우팅
  - 외부 리뷰 수집 시 robots 정책 준수
- **Monetization Domain**
  - 동 단위 로컬 광고 타게팅
  - 프리미엄 안심 리포트 구독
  - O2O 간병인 매칭 수수료

## 4) 권장 기술 스택(예시)

- **Frontend**: Next.js + TypeScript + Map SDK(카카오/네이버/Leaflet)
- **Backend API**: NestJS(or FastAPI) + PostgreSQL + Redis
- **검색**: PostgreSQL PostGIS + OpenSearch(선택)
- **데이터 파이프라인**: Python + Airflow(or Temporal)
- **실시간/비동기**: Kafka(or SQS) + Worker
- **모니터링**: Prometheus/Grafana + OpenTelemetry

## 5) Python 개발 환경

- **Python 3.11+** 권장 (`.python-version`에 3.12 명시)
- 가상 환경 생성 후 `pip install -r requirements.txt`로 의존성 설치
- 테스트: 프로젝트 루트에서 `pytest` 실행
- 상세: [docs/development.md](docs/development.md) 참고

## 6) 빠른 시작 순서

1. `packages/data-pipeline`에서 서울시 API 커넥터 3종 구현
2. `apps/api`에서 시설 검색/상세/리뷰 API 구축
3. `packages/geo-engine`에서 안심 통학/골든타임 지수 계산기 구현
4. `packages/trust-safety`에서 주민 인증+OCR+안심번호 연동
5. `apps/web`에서 MVP 사용자 플로우(검색→비교→문의→리뷰) 완성

상세 설계는 `docs/architecture` 및 `docs/roadmap` 문서를 참고하세요.
