# 데이터 모델 초안 (MVP)

## 주요 엔터티

### facility
- id (PK)
- type (`childcare` | `eldercare` | `community`)
- name
- address
- lat, lng
- district_code (자치구)
- dong_code (행정동)
- source_provider (`seoul_open_data` ...)
- source_updated_at
- attributes (JSONB: 특수학급, 공실, 인증 등)

### safety_infra
- id (PK)
- infra_type (`cctv` | `aed` | `er` | `speed_camera`)
- name
- lat, lng
- coverage_radius_m
- metadata (JSONB)

### review
- id (PK)
- facility_id (FK)
- user_id (FK)
- rating
- content
- resident_verified (bool)
- receipt_verified (bool)
- moderation_status (`pending` | `approved` | `rejected`)
- created_at

### resident_verification
- id (PK)
- user_id (FK)
- dong_code
- geofence_match_score
- verified_at
- expires_at

### golden_time_score
- id (PK)
- facility_id (FK)
- nearest_er_id
- estimated_minutes
- score (0-100)
- computed_at

### ad_campaign
- id (PK)
- advertiser_id
- target_dong_codes (array)
- budget
- status

## 인덱스 권장
- facility: `(type, district_code)`, `GIST(geo_point)`
- review: `(facility_id, moderation_status, created_at DESC)`
- safety_infra: `(infra_type)`, `GIST(geo_point)`

## 데이터 파이프라인 규칙
- 원천 데이터는 `raw_*` 테이블에 적재 후 표준화 테이블로 승격
- 수집 실패/지연은 별도 `ingestion_job_log` 기록
- source_updated_at 기준 증분 적재 우선
