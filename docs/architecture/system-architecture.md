# 시스템 아키텍처 (MVP)

## 상위 구성

1. **Client Layer**
   - 사용자 웹(보호자/학부모)
   - 운영 콘솔(관리자)

2. **Application Layer (API/BFF)**
   - Facility Service: 시설 검색/상세/필터
   - Review Service: 리뷰 등록/검증/노출
   - Match Service: 간병인/시설 문의 및 매칭
   - Report Service: 프리미엄 리포트 생성
   - Auth Service: 사용자 인증/권한

3. **Intelligence Layer**
   - Geo Engine: 통학 안전 경로, 골든타임 지수
   - Trust Engine: 주민 인증, OCR 인증, 이상 리뷰 탐지

4. **Data Layer**
   - OLTP: PostgreSQL(+PostGIS)
   - Cache: Redis
   - Search Index: OpenSearch(선택)
   - Object Storage: 증빙/이미지 파일

5. **Ingestion Layer**
   - 서울 열린데이터 API 커넥터
   - 배치/스트리밍 ETL
   - 데이터 품질 검증(정합성, 결측치, 갱신주기)

6. **Integration Layer**
   - 050 안심번호 제공사
   - OCR 서비스
   - 지도/경로 API

## 핵심 설계 패턴

- **Provider Adapter**
  - `SeoulProvider`, `GyeonggiProvider`, `NationalProvider` 인터페이스로 지역 확장
- **Domain-first Schema**
  - 시설 공통 모델 + 지역별 확장 속성(JSONB)
- **Event-driven Workflow**
  - 리뷰 등록 → 검증 큐 → 노출/보류
  - 신규 데이터 수집 → 품질검증 → 색인 갱신

## 보안 및 컴플라이언스

- 개인정보 최소수집/마스킹
- 리뷰 원문 접근권한 분리(RBAC)
- 외부 콘텐츠 수집 시 robots 정책 검사 선행
- 감사로그(누가/언제/무엇을 변경)
