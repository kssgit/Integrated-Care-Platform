# 서울케어플러스 마이크로서비스 아키텍처 상세 설계 및 개선 방안

## 📋 목차
1. [현재 시스템 분석](#1-현재-시스템-분석)
2. [마이크로서비스 아키텍처 설계](#2-마이크로서비스-아키텍처-설계)
3. [보안 취약점 및 개선 방안](#3-보안-취약점-및-개선-방안)
4. [데이터 파이프라인 개선](#4-데이터-파이프라인-개선)
5. [세분화가 필요한 기능](#5-세분화가-필요한-기능)
6. [구현 우선순위 및 로드맵](#6-구현-우선순위-및-로드맵)

---

## 1. 현재 시스템 분석

### 1.1 기존 구조 평가

**현재 구조 (GitHub 저장소 기준)**:
```
integrated-care-platform/
├── apps/
│   ├── admin/          # 운영 콘솔
│   ├── api/            # BFF/API 서버
│   └── web/            # 웹 프론트엔드
├── packages/
│   ├── data-pipeline/  # ETL 파이프라인
│   ├── geo-engine/     # 지리 엔진
│   ├── shared/         # 공통 라이브러리
│   └── trust-safety/   # 신뢰/안전 모듈
└── infra/
    ├── docker/
    ├── k8s/
    └── terraform/
```

**장점**:
- ✅ 모노레포(Monorepo) 구조로 코드 공유 용이
- ✅ 도메인별 패키지 분리 (data-pipeline, geo-engine, trust-safety)
- ✅ Python 3.11+ 사용으로 최신 기능 활용
- ✅ FastAPI 기반으로 비동기 처리 지원
- ✅ 테스트 환경 구축 (pytest)

**개선이 필요한 영역**:
- ❌ **마이크로서비스 분리 부족**: `apps/api`가 모놀리식 BFF로 구성
- ❌ **데이터베이스 설계 누락**: 스키마 및 관계 정의 필요
- ❌ **메시지 큐 미구현**: Kafka 의존성만 있고 실제 구현 없음
- ❌ **보안 레이어 부재**: 인증/인가, 암호화, API Gateway 미구현
- ❌ **모니터링 불완전**: Prometheus client만 있고 실제 메트릭 수집 미구현
- ❌ **API 스펙 문서화 부재**: OpenAPI/Swagger 문서 없음

---

## 2. 마이크로서비스 아키텍처 설계

### 2.1 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Web Client  │  │ Mobile App   │  │ Admin Portal │                  │
│  │  (Next.js)   │  │ (React Native│  │  (React)     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└──────────────┬──────────────┬──────────────┬────────────────────────────┘
               │              │              │
               └──────────────┴──────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                      API Gateway Layer                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Kong Gateway / AWS API Gateway                                     │  │
│  │  - Rate Limiting (100 req/min per user)                             │  │
│  │  - Authentication (JWT Validation)                                  │  │
│  │  - Request Routing                                                  │  │
│  │  - Response Caching (Redis 5min TTL)                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                    Service Mesh Layer (Istio/Envoy)                        │
│  - Service Discovery                                                       │
│  - Circuit Breaking                                                        │
│  - Distributed Tracing                                                     │
│  - mTLS Encryption                                                         │
└───────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                      Microservices Layer                                   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  User Service      │  │  Auth Service      │  │ Facility Service  │   │
│  │  (사용자 관리)       │  │  (인증/인가)         │  │ (시설 정보)        │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Search Service    │  │  Review Service    │  │ Verification Svc  │   │
│  │  (통합 검색)         │  │  (리뷰 관리)         │  │ (OCR 인증)         │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  AI/ML Service     │  │  Matching Service  │  │ Care Report Svc   │   │
│  │  (추천 엔진)         │  │  (매칭)             │  │ (케어 리포트)       │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Notification Svc  │  │  Payment Service   │  │ Public API Gateway│   │
│  │  (알림)             │  │  (결제/정산)         │  │ (공공 API 통합)     │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Analytics Service │  │  Admin Service     │  │ Privacy Service   │   │
│  │  (분석)             │  │  (관리자)           │  │ (안심번호)          │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                    Message Queue Layer (Kafka)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │ user-events  │  │review-events │  │ care-events  │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
└───────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                       Data Layer                                           │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  PostgreSQL        │  │  MongoDB           │  │ Redis             │   │
│  │  (관계형 데이터)     │  │  (문서형 데이터)     │  │ (캐시/세션)         │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Elasticsearch     │  │  TimescaleDB       │  │ S3/CloudFlare R2  │   │
│  │  (검색 엔진)         │  │  (시계열 데이터)     │  │ (객체 스토리지)      │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                  External Integration Layer                                │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  보건복지부 API     │  │  국민건강보험공단   │  │ 서울시 Open API   │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Naver/Kakao OCR   │  │  Toss Payments     │  │ Twilio/Aligo SMS  │   │
│  └────────────────────┘  └────────────────────┘  └───────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 마이크로서비스 상세 분해 (15개 핵심 서비스)

#### 서비스 1: User Service (사용자 관리)

**책임**: 사용자 계정 및 프로필 관리

**기술 스택**:
- Language: Python (FastAPI) or Node.js (NestJS)
- Database: PostgreSQL
- Cache: Redis
- Message Queue: Kafka

**API Endpoints**:
```python
# 사용자 관리
POST   /api/v1/users                    # 회원가입
GET    /api/v1/users/{user_id}          # 사용자 정보 조회
PUT    /api/v1/users/{user_id}          # 프로필 수정
DELETE /api/v1/users/{user_id}          # 회원 탈퇴
GET    /api/v1/users/{user_id}/preferences  # 사용자 선호도

# 사용자 검색 (관리자용)
GET    /api/v1/users/search             # 사용자 검색
```

**Database Schema**:
```sql
-- PostgreSQL
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_encrypted VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) CHECK (user_type IN ('guardian', 'facility_admin', 'care_worker')),
    profile_data JSONB,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_phone ON users(phone_encrypted) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_type ON users(user_type);

CREATE TABLE user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    care_type VARCHAR(20) CHECK (care_type IN ('child', 'senior', 'community')),
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    search_radius_km INTEGER DEFAULT 5,
    preferred_facilities JSONB,  -- 선호 시설 특성
    notification_settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);
```

**이벤트 발행**:
```python
# Kafka Events
- user.created
- user.updated
- user.deleted
- user.preferences.changed
```

---

#### 서비스 2: Auth Service (인증/인가)

**책임**: 인증, 인가, 세션 관리, 토큰 발급

**API Endpoints**:
```python
POST   /api/v1/auth/register            # 회원가입
POST   /api/v1/auth/login               # 로그인
POST   /api/v1/auth/logout              # 로그아웃
POST   /api/v1/auth/refresh             # 토큰 갱신
POST   /api/v1/auth/verify-email        # 이메일 인증
POST   /api/v1/auth/verify-phone        # 휴대폰 인증
POST   /api/v1/auth/reset-password      # 비밀번호 재설정
POST   /api/v1/auth/change-password     # 비밀번호 변경
GET    /api/v1/auth/me                  # 현재 사용자 정보
```

**보안 요구사항**:
```python
# JWT 토큰 설정
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15분
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7일

# 비밀번호 해싱
- bcrypt (cost factor 12)
- Argon2id (권장)

# Rate Limiting
- 로그인 시도: 5회/5분 (IP 기준)
- OTP 발송: 3회/30분 (전화번호 기준)
- 비밀번호 재설정: 3회/1시간

# 2FA (Two-Factor Authentication)
- SMS OTP (Twilio/Aligo)
- Email OTP
- TOTP (Google Authenticator) - 선택사항
```

**Database Schema**:
```sql
CREATE TABLE auth_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    access_token VARCHAR(500) NOT NULL,
    refresh_token VARCHAR(500) NOT NULL,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_auth_tokens_user ON auth_tokens(user_id);
CREATE INDEX idx_auth_tokens_refresh ON auth_tokens(refresh_token);
CREATE INDEX idx_auth_tokens_expires ON auth_tokens(expires_at);

CREATE TABLE login_attempts (
    attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    email VARCHAR(255),
    ip_address INET NOT NULL,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_login_attempts_ip ON login_attempts(ip_address, attempted_at);
CREATE INDEX idx_login_attempts_email ON login_attempts(email, attempted_at);

CREATE TABLE otp_codes (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    phone_encrypted VARCHAR(255),
    email VARCHAR(255),
    code VARCHAR(6) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('sms', 'email')),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_otp_phone ON otp_codes(phone_encrypted, expires_at);
CREATE INDEX idx_otp_email ON otp_codes(email, expires_at);
```

---

#### 서비스 3: Facility Service (시설 정보 관리)

**책임**: 시설 정보 통합 관리, 공공 API 데이터 동기화

**API Endpoints**:
```python
# 시설 조회
GET    /api/v1/facilities                      # 시설 목록 (페이지네이션)
GET    /api/v1/facilities/{facility_id}        # 시설 상세
GET    /api/v1/facilities/search               # 검색 (텍스트 + 필터)
GET    /api/v1/facilities/nearby               # 주변 시설 (위치 기반)
GET    /api/v1/facilities/{facility_id}/stats  # 시설 통계

# 시설 관리 (운영자/관리자)
POST   /api/v1/facilities                      # 시설 등록
PUT    /api/v1/facilities/{facility_id}        # 시설 정보 수정
DELETE /api/v1/facilities/{facility_id}        # 시설 삭제
POST   /api/v1/facilities/{facility_id}/verify # 시설 인증

# 시설 사진/문서
POST   /api/v1/facilities/{facility_id}/photos # 사진 업로드
GET    /api/v1/facilities/{facility_id}/photos # 사진 목록
DELETE /api/v1/facilities/{facility_id}/photos/{photo_id}
```

**Database Schema**:
```sql
CREATE TABLE facilities (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_type VARCHAR(50) CHECK (facility_type IN ('childcare', 'nursing_home', 'community_center', 'daycare')),
    name VARCHAR(255) NOT NULL,
    address JSONB NOT NULL,  -- {road, jibun, detail, postal_code, district}
    location GEOGRAPHY(POINT, 4326) NOT NULL,  -- PostGIS
    public_api_id VARCHAR(100),  -- 공공 API 연동 ID
    public_api_source VARCHAR(50),  -- 'mohw', 'nhis', 'seoul_open'
    last_synced_at TIMESTAMP WITH TIME ZONE,
    facility_data JSONB,  -- 시설 특화 데이터
    operating_status VARCHAR(20) CHECK (operating_status IN ('active', 'inactive', 'suspended')),
    verification_status VARCHAR(20) CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_facilities_type ON facilities(facility_type);
CREATE INDEX idx_facilities_location ON facilities USING GIST(location);
CREATE INDEX idx_facilities_district ON facilities((address->>'district'));
CREATE INDEX idx_facilities_public_api ON facilities(public_api_source, public_api_id);

-- 아동 돌봄 시설 특화 테이블
CREATE TABLE childcare_facilities (
    facility_id UUID PRIMARY KEY REFERENCES facilities(facility_id) ON DELETE CASCADE,
    capacity INTEGER,
    teacher_child_ratio VARCHAR(10),  -- "1:5"
    cctv_count INTEGER,
    seoul_certified BOOLEAN DEFAULT FALSE,
    special_programs TEXT[],
    meal_cost INTEGER,
    extended_care BOOLEAN,
    age_range_min INTEGER,
    age_range_max INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 노인 요양 시설 특화 테이블
CREATE TABLE nursing_facilities (
    facility_id UUID PRIMARY KEY REFERENCES facilities(facility_id) ON DELETE CASCADE,
    nhis_grade VARCHAR(1) CHECK (nhis_grade IN ('A', 'B', 'C', 'D', 'E')),
    capacity INTEGER,
    current_occupancy INTEGER,
    care_workers_count INTEGER,
    nurses_count INTEGER,
    doctors_count INTEGER,
    specialized_care TEXT[],  -- ["치매 전문", "암 전문"]
    amenities TEXT[],
    monthly_cost_range JSONB,  -- {min, max}
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE facility_photos (
    photo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    photo_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    photo_type VARCHAR(20) CHECK (photo_type IN ('exterior', 'interior', 'facility', 'meal', 'activity', 'panorama')),
    is_panorama BOOLEAN DEFAULT FALSE,
    display_order INTEGER,
    uploaded_by UUID REFERENCES users(user_id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_facility_photos_facility ON facility_photos(facility_id, display_order);
```

**공공 API 연동 전략**:
```python
# 데이터 소스
API_SOURCES = {
    'childcare': {
        'name': '보건복지부 보육통합정보',
        'endpoint': 'http://api.childcare.go.kr/mediate/rest/',
        'sync_interval': 'daily',  # 매일 새벽 3시
        'rate_limit': '1000/hour'
    },
    'nursing': {
        'name': '국민건강보험공단',
        'endpoint': 'https://www.longtermcare.or.kr/npbs/',
        'sync_interval': 'weekly',  # 매주 일요일
        'rate_limit': '500/hour'
    },
    'seoul_open': {
        'name': '서울 열린데이터광장',
        'endpoint': 'http://openapi.seoul.go.kr:8088/',
        'sync_interval': 'hourly',  # 실시간 (캐싱 1시간)
        'rate_limit': '1000/day'
    }
}

# 데이터 동기화 워크플로우
1. API 호출 → 원본 데이터 수집
2. 데이터 정제 및 변환
3. 변경 감지 (CDC - Change Data Capture)
4. 증분 업데이트
5. 캐시 무효화
6. 알림 발송 (관리자)
```

---

#### 서비스 4: Search Service (통합 검색)

**책임**: Elasticsearch 기반 통합 검색, 필터링, 정렬

**기술 스택**:
- Search Engine: Elasticsearch 8.x
- Cache: Redis
- Language: Python (FastAPI)

**API Endpoints**:
```python
GET    /api/v1/search                    # 통합 검색
GET    /api/v1/search/suggest            # 자동완성
GET    /api/v1/search/filters            # 필터 옵션
POST   /api/v1/search/advanced           # 고급 검색
GET    /api/v1/search/trending           # 인기 검색어
```

**Elasticsearch Index Mapping**:
```json
{
  "mappings": {
    "properties": {
      "facility_id": { "type": "keyword" },
      "facility_type": { "type": "keyword" },
      "name": {
        "type": "text",
        "analyzer": "korean",
        "fields": {
          "keyword": { "type": "keyword" },
          "ngram": {
            "type": "text",
            "analyzer": "ngram_analyzer"
          }
        }
      },
      "address": {
        "type": "text",
        "analyzer": "korean",
        "fields": {
          "keyword": { "type": "keyword" }
        }
      },
      "location": { "type": "geo_point" },
      "district": { "type": "keyword" },
      "grade": { "type": "keyword" },
      "rating": { "type": "float" },
      "review_count": { "type": "integer" },
      "capacity": { "type": "integer" },
      "teacher_child_ratio": { "type": "keyword" },
      "seoul_certified": { "type": "boolean" },
      "tags": { "type": "keyword" },
      "certifications": { "type": "keyword" },
      "amenities": { "type": "keyword" },
      "monthly_cost_min": { "type": "integer" },
      "monthly_cost_max": { "type": "integer" },
      "last_synced_at": { "type": "date" },
      "created_at": { "type": "date" }
    }
  },
  "settings": {
    "analysis": {
      "analyzer": {
        "korean": {
          "type": "custom",
          "tokenizer": "nori_tokenizer",
          "filter": ["lowercase", "nori_readingform"]
        },
        "ngram_analyzer": {
          "type": "custom",
          "tokenizer": "ngram_tokenizer",
          "filter": ["lowercase"]
        }
      },
      "tokenizer": {
        "ngram_tokenizer": {
          "type": "ngram",
          "min_gram": 2,
          "max_gram": 3,
          "token_chars": ["letter", "digit"]
        }
      }
    }
  }
}
```

**검색 쿼리 예시**:
```python
# 텍스트 검색 + 지리 검색 + 필터링
def search_facilities(
    query: str,
    lat: float,
    lng: float,
    radius_km: int = 5,
    facility_type: Optional[str] = None,
    grade: Optional[List[str]] = None,
    certified_only: bool = False,
    sort_by: str = "relevance"
) -> Dict:
    
    es_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^3", "address^2", "tags"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "geo_distance": {
                            "distance": f"{radius_km}km",
                            "location": {
                                "lat": lat,
                                "lon": lng
                            }
                        }
                    }
                ],
                "filter": []
            }
        },
        "sort": [],
        "size": 20
    }
    
    # 필터 추가
    if facility_type:
        es_query["query"]["bool"]["filter"].append(
            {"term": {"facility_type": facility_type}}
        )
    
    if grade:
        es_query["query"]["bool"]["filter"].append(
            {"terms": {"grade": grade}}
        )
    
    if certified_only:
        es_query["query"]["bool"]["filter"].append(
            {"term": {"seoul_certified": True}}
        )
    
    # 정렬
    if sort_by == "distance":
        es_query["sort"].append({
            "_geo_distance": {
                "location": {"lat": lat, "lon": lng},
                "order": "asc",
                "unit": "km"
            }
        })
    elif sort_by == "rating":
        es_query["sort"].append({"rating": "desc"})
    elif sort_by == "review_count":
        es_query["sort"].append({"review_count": "desc"})
    else:  # relevance (default)
        es_query["sort"].append({"_score": "desc"})
    
    # Elasticsearch 쿼리 실행
    response = es_client.search(index="facilities", body=es_query)
    
    return {
        "total": response["hits"]["total"]["value"],
        "results": [hit["_source"] for hit in response["hits"]["hits"]]
    }
```

---

#### 서비스 5: Review Service (리뷰 관리)

**책임**: 리뷰 작성, 조회, 신고, 분쟁 처리

**API Endpoints**:
```python
# 리뷰 CRUD
POST   /api/v1/reviews                          # 리뷰 작성
GET    /api/v1/reviews/{facility_id}            # 시설 리뷰 목록
GET    /api/v1/reviews/{review_id}              # 리뷰 상세
PUT    /api/v1/reviews/{review_id}              # 리뷰 수정
DELETE /api/v1/reviews/{review_id}              # 리뷰 삭제

# 리뷰 상호작용
POST   /api/v1/reviews/{review_id}/helpful      # 도움됨 표시
POST   /api/v1/reviews/{review_id}/report       # 리뷰 신고
POST   /api/v1/reviews/{review_id}/reply        # 시설 측 답변

# 리뷰 통계
GET    /api/v1/reviews/{facility_id}/summary    # 리뷰 요약 통계
GET    /api/v1/reviews/{facility_id}/rating-distribution
```

**Database Schema**:
```sql
CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    visit_date DATE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_id UUID,
    verification_method VARCHAR(20) CHECK (verification_method IN ('receipt', 'contract', 'location')),
    trust_score INTEGER CHECK (trust_score BETWEEN 0 AND 100),
    status VARCHAR(20) CHECK (status IN ('active', 'reported', 'blocked', 'deleted')) DEFAULT 'active',
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_reviews_facility ON reviews(facility_id, status, created_at DESC);
CREATE INDEX idx_reviews_user ON reviews(user_id);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_reviews_verified ON reviews(is_verified) WHERE is_verified = TRUE;

CREATE TABLE review_photos (
    photo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(review_id) ON DELETE CASCADE,
    photo_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    is_panorama BOOLEAN DEFAULT FALSE,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE review_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(review_id) ON DELETE CASCADE,
    reporter_id UUID REFERENCES users(user_id),
    reporter_type VARCHAR(20) CHECK (reporter_type IN ('user', 'facility')),
    reason VARCHAR(50) CHECK (reason IN ('defamation', 'false_info', 'inappropriate', 'spam', 'rights_violation')),
    description TEXT,
    evidence_urls TEXT[],
    status VARCHAR(20) CHECK (status IN ('pending', 'reviewing', 'resolved', 'rejected')) DEFAULT 'pending',
    resolution TEXT,
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_review_reports_review ON review_reports(review_id);
CREATE INDEX idx_review_reports_status ON review_reports(status);

CREATE TABLE facility_replies (
    reply_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(review_id) ON DELETE CASCADE,
    facility_id UUID REFERENCES facilities(facility_id),
    user_id UUID REFERENCES users(user_id),  -- 시설 운영자
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_facility_replies_review ON facility_replies(review_id);
```

**리뷰 신뢰도 점수 계산**:
```python
def calculate_trust_score(review: Dict) -> int:
    """리뷰 신뢰도 점수 계산 (0-100)"""
    score = 0
    
    # 1. 인증 여부 (+40점)
    if review.get('is_verified'):
        score += 40
        # 인증 방법별 가중치
        method = review.get('verification_method')
        if method == 'receipt':
            score += 5  # 영수증 인증 (가장 신뢰도 높음)
        elif method == 'contract':
            score += 3  # 계약서 인증
        elif method == 'location':
            score += 2  # 위치 인증
    
    # 2. 사진 첨부 (+20점)
    photo_count = len(review.get('photos', []))
    if photo_count > 0:
        score += min(photo_count * 5, 20)
    
    # 3. 상세한 내용 (+15점)
    content_length = len(review.get('content', ''))
    if content_length > 500:
        score += 15
    elif content_length > 200:
        score += 10
    elif content_length > 100:
        score += 5
    
    # 4. 방문일 기록 (+10점)
    if review.get('visit_date'):
        score += 10
    
    # 5. 도움됨 표시 (최대 +10점)
    helpful_count = review.get('helpful_count', 0)
    score += min(helpful_count // 2, 10)
    
    # 6. 사용자 신뢰도 (최대 +5점)
    user_trust = review.get('user_trust_level', 0)
    score += min(user_trust, 5)
    
    return min(score, 100)
```

**리뷰 분쟁 처리 프로세스**:
```
1. 리뷰 게시 (Review Posted)
   ↓
2. 신고 접수 (Complaint Filed)
   - 시설 측 신고
   - 사용자 신고
   ↓
3. 임시 블라인드 (30일) (Temporary Block)
   - 리뷰 비공개 처리
   - 작성자에게 소명 기회 제공
   ↓
4. 양측 증빙 제출 (Proof Submitted)
   - 작성자: 영수증, 계약서, 사진 등
   - 시설: 반박 증거, 기록 등
   ↓
5. 관리자 검토 (Admin Review)
   - Fact-Based 판단
   - 정보통신망법 제70조 준수
   ↓
6. 결정
   ├─ 복구 (공공의 이익) → 리뷰 재게시
   └─ 영구 삭제 (악성/허위) → 리뷰 영구 삭제
```

---

#### 서비스 6: Verification Service (OCR 인증)

**책임**: OCR 기반 영수증/계약서 인증, 위치 기반 인증

**기술 스택**:
- OCR: Naver Clova OCR / Google Vision API
- Location: Geofencing (PostGIS)
- Storage: S3 / CloudFlare R2

**API Endpoints**:
```python
POST   /api/v1/verification/receipt            # 영수증 인증
POST   /api/v1/verification/contract           # 계약서 인증
POST   /api/v1/verification/location           # 위치 인증
GET    /api/v1/verification/{verification_id}  # 인증 상태 조회
POST   /api/v1/verification/{verification_id}/retry  # 재시도
```

**OCR 처리 워크플로우**:
```
1. 이미지 업로드
   ↓
2. 이미지 전처리
   - 해상도 조정 (최소 1024x768)
   - 회전 보정
   - 노이즈 제거
   ↓
3. OCR 처리
   - Primary: Naver Clova OCR
   - Fallback: Google Vision API
   ↓
4. 데이터 추출
   - 시설명
   - 날짜
   - 금액
   - 영수증/계약서 번호
   ↓
5. 데이터 검증
   - 시설 DB와 매칭 (이름 유사도 > 80%)
   - 날짜 유효성 (과거 2년 이내)
   - 금액 범위 확인
   ↓
6. 인증 완료
   - 리뷰와 연결
   - 신뢰도 점수 상승
```

**Database Schema**:
```sql
CREATE TABLE verifications (
    verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    facility_id UUID,
    type VARCHAR(20) CHECK (type IN ('receipt', 'contract', 'location')) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('pending', 'processing', 'verified', 'rejected', 'failed')) DEFAULT 'pending',
    image_url VARCHAR(500),
    ocr_result JSONB,
    extracted_data JSONB,  -- {facility_name, date, amount, receipt_number}
    confidence_score DECIMAL(5,4),  -- 0.0000 ~ 1.0000
    rejection_reason TEXT,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_verifications_user ON verifications(user_id);
CREATE INDEX idx_verifications_facility ON verifications(facility_id);
CREATE INDEX idx_verifications_status ON verifications(status);

CREATE TABLE location_verifications (
    location_verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_id UUID REFERENCES verifications(verification_id) ON DELETE CASCADE,
    user_location GEOGRAPHY(POINT, 4326),
    facility_location GEOGRAPHY(POINT, 4326),
    distance_meters DECIMAL(10,2),
    is_within_geofence BOOLEAN,
    geofence_radius_meters INTEGER DEFAULT 100,
    verified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**OCR 결과 예시**:
```json
{
  "verification_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "receipt",
  "status": "verified",
  "ocr_result": {
    "provider": "naver_clova",
    "raw_text": "행복어린이집\n2025-02-01\n금액: 350,000원\n영수증번호: 2025020100123",
    "confidence": 0.95,
    "processing_time_ms": 1234
  },
  "extracted_data": {
    "facility_name": "행복어린이집",
    "facility_name_match_score": 0.92,
    "date": "2025-02-01",
    "amount": 350000,
    "receipt_number": "2025020100123",
    "payment_method": "카드"
  },
  "confidence_score": 0.95,
  "verified_at": "2025-02-16T10:30:00Z"
}
```

---

#### 서비스 7: AI/ML Service (추천 엔진)

**책임**: AI 기반 시설 추천, 장기요양 등급 예측, 본인부담금 계산

**기술 스택**:
- ML Framework: TensorFlow / PyTorch / Scikit-learn
- Model Serving: TensorFlow Serving / TorchServe
- Feature Store: Feast
- Vector Database: Milvus (유사도 검색)

**API Endpoints**:
```python
# 추천
POST   /api/v1/recommend/facilities            # 시설 추천
POST   /api/v1/recommend/similar               # 유사 시설 추천
GET    /api/v1/recommend/personalized/{user_id}  # 개인화 추천

# 예측
POST   /api/v1/predict/ltc-grade               # 장기요양 등급 예측
POST   /api/v1/predict/cost-estimate           # 비용 예측
POST   /api/v1/predict/demand-forecast         # 수요 예측

# 모델 관리
GET    /api/v1/models/status                   # 모델 상태
POST   /api/v1/models/retrain                  # 재학습 트리거
```

**추천 알고리즘**:

**1. 협업 필터링 (Collaborative Filtering)**
```python
# User-based CF: 유사한 사용자가 선택한 시설
class UserBasedCF:
    def recommend(self, user_id: str, k: int = 10) -> List[str]:
        # 1. 유사 사용자 찾기 (코사인 유사도)
        similar_users = self.find_similar_users(user_id, top_n=50)
        
        # 2. 유사 사용자들이 선택한 시설
        candidate_facilities = self.get_facilities_of_similar_users(similar_users)
        
        # 3. 점수 계산
        scores = self.calculate_scores(candidate_facilities, similar_users)
        
        # 4. 상위 k개 반환
        return sorted(scores, key=lambda x: x[1], reverse=True)[:k]

# Item-based CF: 유사한 시설 특성
class ItemBasedCF:
    def recommend(self, facility_ids: List[str], k: int = 10) -> List[str]:
        # 1. 시설 특성 벡터화
        facility_vectors = self.vectorize_facilities(facility_ids)
        
        # 2. 유사 시설 찾기
        similar_facilities = self.find_similar_facilities(facility_vectors)
        
        return similar_facilities[:k]
```

**2. 콘텐츠 기반 필터링 (Content-Based)**
```python
class ContentBasedRecommender:
    def __init__(self):
        self.feature_weights = {
            'location': 0.3,
            'grade': 0.2,
            'rating': 0.2,
            'price': 0.15,
            'amenities': 0.1,
            'certifications': 0.05
        }
    
    def create_user_profile(self, user_id: str) -> np.ndarray:
        """사용자 선호도 프로파일 생성"""
        user_prefs = self.get_user_preferences(user_id)
        user_history = self.get_user_history(user_id)
        
        # TF-IDF + 가중평균
        profile_vector = self.weighted_average_of_features(
            user_prefs, 
            user_history,
            self.feature_weights
        )
        
        return profile_vector
    
    def recommend(self, user_id: str, k: int = 10) -> List[str]:
        # 1. 사용자 프로파일 생성
        user_vector = self.create_user_profile(user_id)
        
        # 2. 모든 시설 벡터화
        facility_vectors = self.vectorize_all_facilities()
        
        # 3. 코사인 유사도 계산
        similarities = cosine_similarity(user_vector, facility_vectors)
        
        # 4. 상위 k개 반환
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        
        return [self.facility_ids[i] for i in top_k_indices]
```

**3. 하이브리드 모델**
```python
class HybridRecommender:
    def __init__(self):
        self.cf_model = UserBasedCF()
        self.cb_model = ContentBasedRecommender()
        
        # 가중치 (협업 필터링 70%, 콘텐츠 기반 30%)
        self.cf_weight = 0.7
        self.cb_weight = 0.3
    
    def recommend(self, user_id: str, k: int = 10) -> List[Dict]:
        # 1. CF 추천
        cf_recommendations = self.cf_model.recommend(user_id, k=20)
        
        # 2. CB 추천
        cb_recommendations = self.cb_model.recommend(user_id, k=20)
        
        # 3. 점수 결합
        combined_scores = {}
        for facility_id, score in cf_recommendations:
            combined_scores[facility_id] = score * self.cf_weight
        
        for facility_id, score in cb_recommendations:
            if facility_id in combined_scores:
                combined_scores[facility_id] += score * self.cb_weight
            else:
                combined_scores[facility_id] = score * self.cb_weight
        
        # 4. 정렬 및 반환
        sorted_recommendations = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {
                'facility_id': facility_id,
                'score': score,
                'facility_info': self.get_facility_info(facility_id)
            }
            for facility_id, score in sorted_recommendations[:k]
        ]
```

**4. 장기요양 등급 예측 모델**
```python
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier

class LTCGradePredictor:
    def __init__(self):
        # XGBoost 모델 (정확도 우선)
        self.model = xgb.XGBClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            objective='multi:softmax',
            num_class=5  # 1등급 ~ 5등급
        )
        
        self.feature_names = [
            'age',
            'mobility_score',      # 이동능력 점수
            'cognitive_score',     # 인지능력 점수
            'self_care_score',     # 자기관리 점수
            'daily_living_score',  # 일상생활 점수
            'chronic_diseases',    # 만성질환 개수
            'requires_assistance', # 도움 필요 정도
            'living_alone'         # 독거 여부
        ]
    
    def predict(self, survey_data: Dict) -> Dict:
        """설문 데이터 기반 등급 예측"""
        # 1. 특성 추출
        features = self.extract_features(survey_data)
        
        # 2. 예측
        predicted_grade = self.model.predict([features])[0] + 1  # 1~5등급
        
        # 3. 확률 계산
        probabilities = self.model.predict_proba([features])[0]
        
        # 4. 신뢰도
        confidence = max(probabilities)
        
        return {
            'predicted_grade': predicted_grade,
            'confidence': confidence,
            'probabilities': {
                f'grade_{i+1}': prob 
                for i, prob in enumerate(probabilities)
            },
            'recommendations': self.get_recommendations(predicted_grade)
        }
    
    def extract_features(self, survey_data: Dict) -> List[float]:
        """설문 데이터에서 특성 추출"""
        features = []
        
        features.append(survey_data['age'])
        features.append(self.calculate_mobility_score(survey_data))
        features.append(self.calculate_cognitive_score(survey_data))
        features.append(self.calculate_self_care_score(survey_data))
        features.append(self.calculate_daily_living_score(survey_data))
        features.append(len(survey_data.get('chronic_diseases', [])))
        features.append(survey_data.get('requires_assistance', 0))
        features.append(1 if survey_data.get('living_alone') else 0)
        
        return features
```

**5. 본인부담금 계산기**
```python
class CostCalculator:
    def __init__(self):
        # 2025년 장기요양급여 비용 (월 한도액)
        self.rate_table = {
            '1급': {
                'home': 1613000,
                'facility': 2064000
            },
            '2급': {
                'home': 1414000,
                'facility': 1836000
            },
            '3급': {
                'home': 1329000,
                'facility': 1548000
            },
            '4급': {
                'home': 1261000,
                'facility': 1417000
            },
            '5급': {
                'home': 1002000,
                'facility': 1308000
            }
        }
        
        # 본인부담률
        self.copayment_rates = {
            'home': 0.15,      # 재가 15%
            'facility': 0.20   # 시설 20%
        }
        
        # 감면 대상
        self.exemption_rates = {
            'basic_livelihood': 0.0,   # 기초생활수급자 0%
            'medical_aid': 0.0,        # 의료급여 0%
            'low_income': 0.50         # 차상위계층 50% 감면
        }
    
    def calculate(
        self,
        grade: str,
        service_type: str,  # 'home' or 'facility'
        exemption_type: Optional[str] = None
    ) -> Dict:
        """본인부담금 계산"""
        
        # 1. 기본 급여액
        base_amount = self.rate_table[grade][service_type]
        
        # 2. 본인부담률
        copayment_rate = self.copayment_rates[service_type]
        
        # 3. 감면 적용
        if exemption_type and exemption_type in self.exemption_rates:
            copayment_rate *= self.exemption_rates[exemption_type]
        
        # 4. 본인부담금
        copayment = int(base_amount * copayment_rate)
        
        # 5. 비급여 비용 (식비 등)
        non_covered = {
            'meal': 150000,      # 월 식비
            'personal': 50000,   # 개인용품비
            'utilities': 30000   # 기타
        }
        
        total_non_covered = sum(non_covered.values())
        
        # 6. 총 비용
        total_cost = copayment + total_non_covered
        
        return {
            'grade': grade,
            'service_type': service_type,
            'base_amount': base_amount,
            'copayment_rate': copayment_rate,
            'copayment': copayment,
            'non_covered_costs': non_covered,
            'total_non_covered': total_non_covered,
            'total_monthly_cost': total_cost,
            'breakdown': {
                'covered_by_insurance': base_amount - copayment,
                'user_payment': total_cost
            }
        }
```

---

#### 서비스 8: Matching Service (매칭 및 예약)

**책임**: 입소 신청, 대기 관리, 매칭 알고리즘

**API Endpoints**:
```python
# 신청 관리
POST   /api/v1/matching/apply                  # 입소/등록 신청
GET    /api/v1/matching/applications/{user_id} # 신청 내역
PUT    /api/v1/matching/{match_id}/status      # 상태 변경
DELETE /api/v1/matching/{match_id}             # 신청 취소

# 대기 관리
GET    /api/v1/matching/waitlist/{facility_id} # 대기 목록
POST   /api/v1/matching/waitlist/{facility_id}/join  # 대기열 등록
GET    /api/v1/matching/waitlist/my-position   # 내 대기 순위

# 매칭 알고리즘
POST   /api/v1/matching/optimal-match          # 최적 매칭 추천
```

**Database Schema**:
```sql
CREATE TABLE match_applications (
    application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    application_type VARCHAR(20) CHECK (application_type IN ('reservation', 'waitlist', 'inquiry')) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('pending', 'accepted', 'rejected', 'cancelled', 'expired')) DEFAULT 'pending',
    priority_score INTEGER,
    application_data JSONB,  -- {preferred_date, special_needs, urgency, etc.}
    rejection_reason TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_match_applications_user ON match_applications(user_id, status);
CREATE INDEX idx_match_applications_facility ON match_applications(facility_id, status);
CREATE INDEX idx_match_applications_priority ON match_applications(priority_score DESC);

CREATE TABLE waitlist (
    waitlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    application_id UUID REFERENCES match_applications(application_id),
    position INTEGER,
    estimated_date DATE,
    priority_score INTEGER,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notified_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(facility_id, user_id)
);

CREATE INDEX idx_waitlist_facility ON waitlist(facility_id, position);
CREATE INDEX idx_waitlist_user ON waitlist(user_id);
```

**우선순위 점수 알고리즘**:
```python
def calculate_priority_score(application: Dict) -> int:
    """
    우선순위 점수 계산 (0-100)
    높을수록 우선순위 높음
    """
    score = 0
    
    # 1. 긴급도 (0-30점)
    urgency = application.get('urgency')
    if urgency == 'critical':     # 긴급
        score += 30
    elif urgency == 'high':       # 높음
        score += 20
    elif urgency == 'medium':     # 보통
        score += 10
    elif urgency == 'low':        # 낮음
        score += 5
    
    # 2. 거리 (0-25점)
    # 가까울수록 높은 점수
    distance_km = application.get('distance_km', 10)
    distance_score = max(25 - distance_km * 2, 0)
    score += int(distance_score)
    
    # 3. 대기 기간 (0-20점)
    # 오래 기다릴수록 높은 점수
    days_waiting = application.get('days_waiting', 0)
    waiting_score = min(days_waiting // 3, 20)  # 3일당 1점, 최대 20점
    score += waiting_score
    
    # 4. 취약계층 가점 (0-15점)
    vulnerable_groups = application.get('vulnerable_groups', [])
    if 'basic_livelihood' in vulnerable_groups:  # 기초생활수급자
        score += 15
    elif 'disabled' in vulnerable_groups:        # 장애인
        score += 10
    elif 'single_parent' in vulnerable_groups:   # 한부모가정
        score += 8
    elif 'multicultural' in vulnerable_groups:   # 다문화가정
        score += 5
    
    # 5. 특수 요구사항 매칭 (0-10점)
    special_needs = application.get('special_needs', [])
    facility_amenities = application.get('facility_amenities', [])
    
    # 요구사항과 시설 편의시설 매칭률
    if special_needs and facility_amenities:
        match_rate = len(set(special_needs) & set(facility_amenities)) / len(special_needs)
        score += int(match_rate * 10)
    
    return min(score, 100)
```

**최적 매칭 알고리즘** (헝가리안 알고리즘 변형):
```python
from scipy.optimize import linear_sum_assignment

class OptimalMatcher:
    def find_optimal_matches(
        self,
        applicants: List[Dict],
        facilities: List[Dict]
    ) -> List[Tuple[str, str, float]]:
        """
        최적 매칭 찾기
        - 신청자와 시설 간 최적 조합
        - 최대 만족도 달성
        """
        
        # 1. 비용 행렬 생성 (cost matrix)
        # 비용이 낮을수록 좋은 매칭
        n_applicants = len(applicants)
        n_facilities = len(facilities)
        cost_matrix = np.zeros((n_applicants, n_facilities))
        
        for i, applicant in enumerate(applicants):
            for j, facility in enumerate(facilities):
                # 매칭 점수 계산 (높을수록 좋음)
                match_score = self.calculate_match_score(applicant, facility)
                
                # 비용으로 변환 (낮을수록 좋게)
                cost_matrix[i][j] = 100 - match_score
        
        # 2. 헝가리안 알고리즘 적용
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # 3. 결과 반환
        matches = []
        for i, j in zip(row_ind, col_ind):
            match_score = 100 - cost_matrix[i][j]
            if match_score >= 50:  # 최소 매칭 점수 50점 이상
                matches.append((
                    applicants[i]['user_id'],
                    facilities[j]['facility_id'],
                    match_score
                ))
        
        return matches
    
    def calculate_match_score(
        self,
        applicant: Dict,
        facility: Dict
    ) -> float:
        """
        신청자-시설 매칭 점수 계산 (0-100)
        """
        score = 0
        
        # 1. 거리 점수 (30점)
        distance = self.calculate_distance(
            applicant['location'],
            facility['location']
        )
        distance_score = max(30 - distance * 3, 0)
        score += distance_score
        
        # 2. 시설 등급 점수 (20점)
        grade_preference = applicant.get('preferred_grade', [])
        if facility['grade'] in grade_preference:
            score += 20
        
        # 3. 시설 특성 매칭 (20점)
        special_needs = set(applicant.get('special_needs', []))
        facility_amenities = set(facility.get('amenities', []))
        
        if special_needs:
            match_rate = len(special_needs & facility_amenities) / len(special_needs)
            score += match_rate * 20
        else:
            score += 20  # 특별 요구사항 없으면 만점
        
        # 4. 가격 범위 매칭 (15점)
        budget = applicant.get('budget', {})
        facility_cost = facility.get('monthly_cost', 0)
        
        if budget.get('min', 0) <= facility_cost <= budget.get('max', float('inf')):
            score += 15
        
        # 5. 시설 평점 (15점)
        rating = facility.get('rating', 0)
        score += (rating / 5.0) * 15
        
        return min(score, 100)
```

---

#### 서비스 9: Care Report Service (케어 리포트)

**책임**: 실시간 케어 기록, 멀티모달 분석, 이상 패턴 감지

**기술 스택**:
- Database: TimescaleDB (시계열)
- ML: TensorFlow / PyTorch (이상 감지)
- Speech-to-Text: Google Cloud Speech API
- Image Recognition: AWS Rekognition

**API Endpoints**:
```python
# 케어 기록
POST   /api/v1/care-reports                    # 케어 기록 작성
GET    /api/v1/care-reports/{user_id}/daily    # 일별 리포트
GET    /api/v1/care-reports/{user_id}/weekly   # 주간 요약
GET    /api/v1/care-reports/{user_id}/monthly  # 월간 요약

# AI 분석
POST   /api/v1/care-reports/analyze            # AI 분석 요청
GET    /api/v1/care-reports/{user_id}/anomalies  # 이상 패턴

# 멀티모달 입력
POST   /api/v1/care-reports/voice              # 음성 기록
POST   /api/v1/care-reports/photo              # 사진 기록
POST   /api/v1/care-reports/sensor             # 센서 데이터
```

**Database Schema (TimescaleDB)**:
```sql
-- 케어 기록
CREATE TABLE care_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    care_recipient_id UUID,  -- 돌봄 대상자 (노인, 아동)
    record_type VARCHAR(50) CHECK (record_type IN ('meal', 'sleep', 'activity', 'medication', 'health', 'behavior', 'mood')),
    recorded_by UUID NOT NULL,  -- 기록자 (요양보호사, 교사)
    input_type VARCHAR(20) CHECK (input_type IN ('text', 'voice', 'photo', 'sensor')),
    content TEXT,
    media_urls TEXT[],
    ai_analysis JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB Hypertable 생성
SELECT create_hypertable('care_records', 'recorded_at');

-- 인덱스
CREATE INDEX idx_care_records_user ON care_records(user_id, recorded_at DESC);
CREATE INDEX idx_care_records_facility ON care_records(facility_id, recorded_at DESC);
CREATE INDEX idx_care_records_type ON care_records(record_type);

-- 건강 메트릭 (시계열 데이터)
CREATE TABLE health_metrics (
    time TIMESTAMPTZ NOT NULL,
    user_id UUID NOT NULL,
    care_recipient_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- 'heart_rate', 'blood_pressure', 'temperature', 'weight', 'sleep_hours', 'meal_intake'
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    device_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hypertable 생성
SELECT create_hypertable('health_metrics', 'time');

-- 인덱스
CREATE INDEX idx_health_metrics_recipient ON health_metrics(care_recipient_id, metric_type, time DESC);
```

**AI 이상 패턴 감지**:
```python
import numpy as np
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.seasonal import seasonal_decompose

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(
            contamination=0.05,  # 5% 이상치
            random_state=42
        )
        
        self.thresholds = {
            'heart_rate': {'min': 60, 'max': 100},
            'blood_pressure_systolic': {'min': 90, 'max': 140},
            'blood_pressure_diastolic': {'min': 60, 'max': 90},
            'temperature': {'min': 36.0, 'max': 37.5},
            'sleep_hours': {'min': 6, 'max': 10},
            'meal_intake': {'min': 60, 'max': 100}  # % of normal intake
        }
    
    def detect_anomalies(
        self,
        user_id: str,
        metric_type: str,
        days: int = 30
    ) -> Dict:
        """이상 패턴 감지"""
        
        # 1. 최근 데이터 수집
        historical_data = self.get_historical_data(
            user_id,
            metric_type,
            days=days
        )
        
        if len(historical_data) < 10:
            return {'status': 'insufficient_data'}
        
        # 2. 통계 분석
        stats = self.calculate_statistics(historical_data)
        
        # 3. 절대 임계값 체크
        threshold_anomalies = self.check_thresholds(
            historical_data[-1],  # 최신 값
            metric_type
        )
        
        # 4. 상대 이상 감지 (Z-score)
        z_score_anomalies = self.detect_z_score_anomalies(
            historical_data,
            threshold=2.5
        )
        
        # 5. 시계열 이상 감지 (Isolation Forest)
        ml_anomalies = self.detect_ml_anomalies(historical_data)
        
        # 6. 트렌드 분석
        trend_analysis = self.analyze_trend(historical_data)
        
        # 7. 종합 판단
        is_anomaly = (
            threshold_anomalies['is_anomaly'] or
            z_score_anomalies['is_anomaly'] or
            ml_anomalies['is_anomaly']
        )
        
        severity = self.calculate_severity(
            threshold_anomalies,
            z_score_anomalies,
            ml_anomalies
        )
        
        return {
            'is_anomaly': is_anomaly,
            'severity': severity,  # 'low', 'medium', 'high', 'critical'
            'current_value': historical_data[-1],
            'statistics': stats,
            'threshold_check': threshold_anomalies,
            'z_score_check': z_score_anomalies,
            'ml_check': ml_anomalies,
            'trend': trend_analysis,
            'recommendation': self.get_recommendation(
                metric_type,
                is_anomaly,
                severity
            )
        }
    
    def detect_z_score_anomalies(
        self,
        data: List[float],
        threshold: float = 2.5
    ) -> Dict:
        """Z-score 기반 이상 감지"""
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return {'is_anomaly': False, 'z_score': 0}
        
        current_value = data[-1]
        z_score = (current_value - mean) / std
        
        is_anomaly = abs(z_score) > threshold
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'mean': mean,
            'std': std,
            'threshold': threshold,
            'message': f'{metric_type} 수치가 평균에서 {abs(z_score):.2f} 표준편차 벗어남'
        }
    
    def detect_ml_anomalies(self, data: List[float]) -> Dict:
        """Isolation Forest 기반 이상 감지"""
        
        # 특성 엔지니어링
        features = self.create_features(data)
        
        # 모델 학습 (온라인 학습)
        self.model.fit(features)
        
        # 최신 데이터 예측
        prediction = self.model.predict([features[-1]])[0]
        anomaly_score = self.model.score_samples([features[-1]])[0]
        
        is_anomaly = (prediction == -1)
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'confidence': abs(anomaly_score)
        }
    
    def create_features(self, data: List[float]) -> np.ndarray:
        """시계열 데이터 특성 생성"""
        
        features = []
        
        for i in range(1, len(data)):
            feature_vector = [
                data[i],                        # 현재 값
                data[i] - data[i-1],           # 변화량
                np.mean(data[max(0,i-7):i+1]), # 7일 이동평균
                np.std(data[max(0,i-7):i+1])   # 7일 표준편차
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def analyze_trend(self, data: List[float]) -> Dict:
        """트렌드 분석"""
        
        if len(data) < 14:
            return {'status': 'insufficient_data'}
        
        # 시계열 분해 (트렌드, 계절성, 잔차)
        decomposition = seasonal_decompose(
            data,
            model='additive',
            period=7  # 주간 패턴
        )
        
        trend = decomposition.trend
        
        # 트렌드 방향
        recent_trend = trend[-7:]
        trend_direction = 'increasing' if recent_trend[-1] > recent_trend[0] else 'decreasing'
        trend_strength = abs(recent_trend[-1] - recent_trend[0]) / recent_trend[0]
        
        return {
            'direction': trend_direction,
            'strength': trend_strength,
            'is_significant': trend_strength > 0.1  # 10% 이상 변화
        }
    
    def get_recommendation(
        self,
        metric_type: str,
        is_anomaly: bool,
        severity: str
    ) -> str:
        """권장사항 생성"""
        
        if not is_anomaly:
            return "정상 범위입니다."
        
        recommendations = {
            'heart_rate': {
                'high': "심박수가 높습니다. 의료진 상담을 권장합니다.",
                'critical': "심박수가 매우 높습니다. 즉시 의료진에게 연락하세요."
            },
            'blood_pressure': {
                'high': "혈압이 높습니다. 지속적인 모니터링이 필요합니다.",
                'critical': "혈압이 매우 높습니다. 즉시 의료 조치가 필요합니다."
            },
            'temperature': {
                'high': "체온이 높습니다. 발열 여부를 확인하세요.",
                'critical': "고열입니다. 즉시 의료진에게 연락하세요."
            },
            'sleep_hours': {
                'low': "수면 시간이 부족합니다. 수면 패턴 개선이 필요합니다."
            },
            'meal_intake': {
                'low': "식사량이 감소했습니다. 식욕 저하 원인을 확인하세요."
            }
        }
        
        return recommendations.get(metric_type, {}).get(severity, "이상 패턴이 감지되었습니다.")
```

---

이 문서는 여기까지이며, 계속해서 나머지 서비스들 (Notification, Payment, Public API Gateway, Analytics, Privacy Service 등)과 보안 취약점, 데이터 파이프라인 개선 방안을 다음 파트에서 작성하겠습니다.

문서가 매우 길어서 여러 파일로 나누어 작성하는 것이 좋을 것 같습니다. 계속 진행할까요?
