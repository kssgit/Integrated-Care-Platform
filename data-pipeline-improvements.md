# 서울케어플러스 데이터 파이프라인 개선 방안

## 📋 목차
1. [현재 데이터 파이프라인 분석](#1-현재-데이터-파이프라인-분석)
2. [개선된 ETL 아키텍처](#2-개선된-etl-아키텍처)
3. [실시간 데이터 파이프라인](#3-실시간-데이터-파이프라인)
4. [데이터 품질 관리](#4-데이터-품질-관리)
5. [배치 처리 최적화](#5-배치-처리-최적화)
6. [모니터링 및 알림](#6-모니터링-및-알림)

---

## 1. 현재 데이터 파이프라인 분석

### 1.1 기존 구조의 문제점

**❌ 식별된 문제점**:

1. **데이터 동기화 전략 부재**
   - 공공 API 데이터 갱신 주기 미정의
   - 증분 업데이트 vs 전체 업데이트 전략 없음
   - 변경 감지 (CDC) 메커니즘 없음

2. **에러 처리 부족**
   - API 호출 실패 시 재시도 로직 없음
   - Dead Letter Queue (DLQ) 미구현
   - 부분 실패 처리 전략 없음

3. **데이터 품질 검증 미흡**
   - 데이터 스키마 검증 없음
   - 이상치 탐지 없음
   - 데이터 일관성 체크 없음

4. **모니터링 및 알림 부재**
   - 파이프라인 상태 모니터링 없음
   - 실패 알림 시스템 없음
   - 성능 메트릭 수집 없음

5. **확장성 제한**
   - 단일 프로세스로 실행
   - 병렬 처리 없음
   - 대용량 데이터 처리 불가

---

## 2. 개선된 ETL 아키텍처

### 2.1 전체 데이터 파이프라인 구조

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Data Sources (공공 API)                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐ │
│  │ 보건복지부 API  │  │ 국민건강보험공단 │  │ 서울 열린데이터광장      │ │
│  │ (어린이집)      │  │ (요양시설)       │  │ (지역센터, 복지시설)    │ │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘ │
└──────────────┬─────────────────┬──────────────────┬────────────────────────┘
               │                 │                  │
               └─────────────────┴──────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                    API Gateway & Rate Limiter                               │
│  - Request Throttling                                                       │
│  - API Key Rotation                                                         │
│  - Circuit Breaker Pattern                                                  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                         Data Ingestion Layer                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Apache Airflow DAGs                                                 │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │  │
│  │  │ Childcare    │  │ Nursing Home │  │  Community Center       │  │  │
│  │  │ Sync DAG     │  │  Sync DAG    │  │  Sync DAG               │  │  │
│  │  │ (Daily 3AM)  │  │ (Weekly Sun) │  │  (Hourly)               │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                       Data Processing Layer                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Apache Spark / Pandas                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │  │
│  │  │  Transform   │  │  Validate    │  │  Enrich                   │ │  │
│  │  │  (Normalize) │  │  (Quality)   │  │  (Geocoding, Scoring)     │ │  │
│  │  └──────────────┘  └──────────────┘  └───────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                      Change Data Capture (CDC)                              │
│  - Detect Changes (Insert/Update/Delete)                                   │
│  - Generate Delta Records                                                   │
│  - Version Management                                                       │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                         Data Storage Layer                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │  │
│  │  │  Data Lake   │  │  PostgreSQL  │  │  Elasticsearch             │ │  │
│  │  │  (S3/Parquet)│  │  (OLTP)      │  │  (Search)                  │ │  │
│  │  └──────────────┘  └──────────────┘  └────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐                                  │  │
│  │  │   Redis      │  │   BigQuery   │                                  │  │
│  │  │   (Cache)    │  │   (OLAP)     │                                  │  │
│  │  └──────────────┘  └──────────────┘                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────────┐
│                     Downstream Consumers                                    │
│  - API Services                                                             │
│  - Analytics Dashboard                                                      │
│  - ML Training Pipeline                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Apache Airflow DAG 구현

**어린이집 데이터 동기화 DAG**:

```python
# dags/sync_childcare_facilities.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.dates import days_ago
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email': ['alerts@seoulcareplus.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2)
}

dag = DAG(
    'sync_childcare_facilities',
    default_args=default_args,
    description='보건복지부 어린이집 데이터 동기화',
    schedule_interval='0 3 * * *',  # 매일 새벽 3시
    start_date=days_ago(1),
    catchup=False,
    tags=['public-api', 'childcare', 'daily']
)

# Task 1: API 건강 체크
check_api_health = HttpSensor(
    task_id='check_api_health',
    http_conn_id='mohw_api',
    endpoint='/status',
    request_params={},
    response_check=lambda response: response.status_code == 200,
    poke_interval=30,
    timeout=300,
    dag=dag
)

# Task 2: 데이터 추출
def extract_childcare_data(**context):
    """보건복지부 API에서 어린이집 데이터 추출"""
    from data_pipeline.extractors.childcare_extractor import ChildcareExtractor
    
    extractor = ChildcareExtractor()
    
    try:
        # 서울시 25개 구 데이터 추출
        seoul_districts = [
            '종로구', '중구', '용산구', '성동구', '광진구',
            '동대문구', '중랑구', '성북구', '강북구', '도봉구',
            '노원구', '은평구', '서대문구', '마포구', '양천구',
            '강서구', '구로구', '금천구', '영등포구', '동작구',
            '관악구', '서초구', '강남구', '송파구', '강동구'
        ]
        
        all_facilities = []
        
        for district in seoul_districts:
            logger.info(f"Extracting data for {district}")
            
            facilities = extractor.fetch_by_district(district)
            all_facilities.extend(facilities)
            
            # API Rate Limiting 준수
            time.sleep(1)
        
        logger.info(f"Extracted {len(all_facilities)} facilities")
        
        # XCom으로 다음 Task에 전달
        context['task_instance'].xcom_push(
            key='raw_facilities',
            value=all_facilities
        )
        
        return len(all_facilities)
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise

extract_data = PythonOperator(
    task_id='extract_childcare_data',
    python_callable=extract_childcare_data,
    provide_context=True,
    dag=dag
)

# Task 3: 데이터 변환 및 검증
def transform_and_validate(**context):
    """데이터 변환 및 품질 검증"""
    from data_pipeline.transformers.childcare_transformer import ChildcareTransformer
    from data_pipeline.validators.data_validator import DataValidator
    
    # XCom에서 데이터 가져오기
    raw_facilities = context['task_instance'].xcom_pull(
        task_ids='extract_childcare_data',
        key='raw_facilities'
    )
    
    transformer = ChildcareTransformer()
    validator = DataValidator()
    
    # 데이터 변환
    transformed_facilities = []
    validation_errors = []
    
    for raw_facility in raw_facilities:
        try:
            # 변환
            facility = transformer.transform(raw_facility)
            
            # 검증
            is_valid, errors = validator.validate_facility(facility)
            
            if is_valid:
                transformed_facilities.append(facility)
            else:
                validation_errors.append({
                    'facility_name': raw_facility.get('stcode_nm'),
                    'errors': errors
                })
                
        except Exception as e:
            logger.error(f"Transform failed for facility: {e}")
            validation_errors.append({
                'facility_name': raw_facility.get('stcode_nm'),
                'error': str(e)
            })
    
    # 검증 에러 로깅
    if validation_errors:
        logger.warning(f"Validation errors: {len(validation_errors)}")
        for error in validation_errors[:10]:  # 처음 10개만 로그
            logger.warning(error)
    
    # 성공률 체크
    success_rate = len(transformed_facilities) / len(raw_facilities)
    
    if success_rate < 0.9:  # 90% 미만이면 실패
        raise ValueError(f"Success rate too low: {success_rate:.2%}")
    
    logger.info(f"Transformed {len(transformed_facilities)} facilities (success rate: {success_rate:.2%})")
    
    # 다음 Task로 전달
    context['task_instance'].xcom_push(
        key='transformed_facilities',
        value=transformed_facilities
    )
    
    return len(transformed_facilities)

transform_data = PythonOperator(
    task_id='transform_and_validate',
    python_callable=transform_and_validate,
    provide_context=True,
    dag=dag
)

# Task 4: CDC (Change Data Capture)
def detect_changes(**context):
    """변경 사항 감지"""
    from data_pipeline.cdc.change_detector import ChangeDetector
    
    transformed_facilities = context['task_instance'].xcom_pull(
        task_ids='transform_and_validate',
        key='transformed_facilities'
    )
    
    detector = ChangeDetector()
    
    # 변경 사항 감지
    changes = detector.detect_changes(
        new_data=transformed_facilities,
        data_source='childcare_facilities'
    )
    
    logger.info(f"Changes detected:")
    logger.info(f"  - Inserts: {len(changes['inserts'])}")
    logger.info(f"  - Updates: {len(changes['updates'])}")
    logger.info(f"  - Deletes: {len(changes['deletes'])}")
    
    # 다음 Task로 전달
    context['task_instance'].xcom_push(
        key='changes',
        value=changes
    )
    
    return changes

detect_changes_task = PythonOperator(
    task_id='detect_changes',
    python_callable=detect_changes,
    provide_context=True,
    dag=dag
)

# Task 5: 데이터베이스 적재
def load_to_database(**context):
    """변경 사항을 데이터베이스에 적재"""
    from data_pipeline.loaders.database_loader import DatabaseLoader
    
    changes = context['task_instance'].xcom_pull(
        task_ids='detect_changes',
        key='changes'
    )
    
    loader = DatabaseLoader()
    
    # 트랜잭션으로 적재
    try:
        loader.begin_transaction()
        
        # Insert
        if changes['inserts']:
            loader.bulk_insert('facilities', changes['inserts'])
            logger.info(f"Inserted {len(changes['inserts'])} facilities")
        
        # Update
        if changes['updates']:
            loader.bulk_update('facilities', changes['updates'])
            logger.info(f"Updated {len(changes['updates'])} facilities")
        
        # Delete (Soft Delete)
        if changes['deletes']:
            loader.soft_delete('facilities', changes['deletes'])
            logger.info(f"Deleted {len(changes['deletes'])} facilities")
        
        loader.commit_transaction()
        
        return {
            'inserts': len(changes['inserts']),
            'updates': len(changes['updates']),
            'deletes': len(changes['deletes'])
        }
        
    except Exception as e:
        loader.rollback_transaction()
        logger.error(f"Load failed: {e}")
        raise

load_data = PythonOperator(
    task_id='load_to_database',
    python_callable=load_to_database,
    provide_context=True,
    dag=dag
)

# Task 6: Elasticsearch 인덱싱
def index_to_elasticsearch(**context):
    """Elasticsearch에 인덱싱"""
    from data_pipeline.indexers.elasticsearch_indexer import ElasticsearchIndexer
    
    changes = context['task_instance'].xcom_pull(
        task_ids='detect_changes',
        key='changes'
    )
    
    indexer = ElasticsearchIndexer()
    
    # Insert + Update만 인덱싱
    documents_to_index = changes['inserts'] + changes['updates']
    
    if documents_to_index:
        indexer.bulk_index(
            index='facilities',
            documents=documents_to_index
        )
        logger.info(f"Indexed {len(documents_to_index)} documents to Elasticsearch")
    
    # Delete는 제거
    if changes['deletes']:
        indexer.bulk_delete(
            index='facilities',
            document_ids=[d['facility_id'] for d in changes['deletes']]
        )
        logger.info(f"Deleted {len(changes['deletes'])} documents from Elasticsearch")
    
    return len(documents_to_index)

index_data = PythonOperator(
    task_id='index_to_elasticsearch',
    python_callable=index_to_elasticsearch,
    provide_context=True,
    dag=dag
)

# Task 7: 캐시 무효화
def invalidate_cache(**context):
    """Redis 캐시 무효화"""
    import redis
    
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # 시설 관련 캐시 키 패턴
    cache_patterns = [
        'facilities:*',
        'search:*',
        'nearby:*'
    ]
    
    invalidated_count = 0
    
    for pattern in cache_patterns:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            invalidated_count += len(keys)
    
    logger.info(f"Invalidated {invalidated_count} cache keys")
    
    return invalidated_count

invalidate_cache_task = PythonOperator(
    task_id='invalidate_cache',
    python_callable=invalidate_cache,
    provide_context=True,
    dag=dag
)

# Task 8: 데이터 품질 메트릭 기록
def record_metrics(**context):
    """데이터 품질 메트릭 기록"""
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
    
    load_result = context['task_instance'].xcom_pull(
        task_ids='load_to_database'
    )
    
    registry = CollectorRegistry()
    
    # Prometheus 메트릭
    inserts_gauge = Gauge(
        'data_pipeline_inserts_total',
        'Total inserts',
        ['source'],
        registry=registry
    )
    updates_gauge = Gauge(
        'data_pipeline_updates_total',
        'Total updates',
        ['source'],
        registry=registry
    )
    deletes_gauge = Gauge(
        'data_pipeline_deletes_total',
        'Total deletes',
        ['source'],
        registry=registry
    )
    
    inserts_gauge.labels(source='childcare').set(load_result['inserts'])
    updates_gauge.labels(source='childcare').set(load_result['updates'])
    deletes_gauge.labels(source='childcare').set(load_result['deletes'])
    
    # Pushgateway로 전송
    push_to_gateway(
        'localhost:9091',
        job='data_pipeline',
        registry=registry
    )
    
    logger.info("Metrics pushed to Prometheus")

record_metrics_task = PythonOperator(
    task_id='record_metrics',
    python_callable=record_metrics,
    provide_context=True,
    dag=dag
)

# Task 9: 알림 발송
def send_notification(**context):
    """처리 완료 알림"""
    from data_pipeline.notifiers.slack_notifier import SlackNotifier
    
    load_result = context['task_instance'].xcom_pull(
        task_ids='load_to_database'
    )
    
    notifier = SlackNotifier()
    
    message = f"""
    ✅ 어린이집 데이터 동기화 완료
    
    📊 처리 결과:
    - 신규: {load_result['inserts']}개
    - 수정: {load_result['updates']}개
    - 삭제: {load_result['deletes']}개
    
    ⏰ 완료 시간: {context['execution_date'].strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    notifier.send(
        channel='#data-pipeline',
        message=message
    )

send_notification_task = PythonOperator(
    task_id='send_notification',
    python_callable=send_notification,
    provide_context=True,
    dag=dag
)

# DAG 의존성 정의
check_api_health >> extract_data >> transform_data >> detect_changes_task
detect_changes_task >> [load_data, index_data]
load_data >> invalidate_cache_task >> record_metrics_task >> send_notification_task
index_data >> record_metrics_task
```

### 2.3 CDC (Change Data Capture) 구현

```python
# data_pipeline/cdc/change_detector.py
from typing import Dict, List
import hashlib
import json

class ChangeDetector:
    """데이터 변경 감지"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def detect_changes(
        self,
        new_data: List[Dict],
        data_source: str
    ) -> Dict[str, List[Dict]]:
        """
        신규 데이터와 기존 데이터를 비교하여 변경 사항 감지
        
        Returns:
            {
                'inserts': [],  # 신규
                'updates': [],  # 수정
                'deletes': []   # 삭제
            }
        """
        
        # 1. 기존 데이터 로드
        existing_data = self._load_existing_data(data_source)
        
        # 2. 해시맵 생성 (빠른 조회)
        existing_map = {
            record['public_api_id']: record 
            for record in existing_data
        }
        
        new_map = {
            record['public_api_id']: record 
            for record in new_data
        }
        
        # 3. 변경 사항 분류
        inserts = []
        updates = []
        deletes = []
        
        # 신규 및 수정
        for api_id, new_record in new_map.items():
            if api_id not in existing_map:
                # 신규
                inserts.append(new_record)
            else:
                # 수정 여부 확인 (해시 비교)
                existing_record = existing_map[api_id]
                
                if self._has_changed(existing_record, new_record):
                    updates.append({
                        **new_record,
                        'facility_id': existing_record['facility_id']  # 기존 ID 유지
                    })
        
        # 삭제 (기존에는 있지만 신규 데이터에 없음)
        for api_id, existing_record in existing_map.items():
            if api_id not in new_map:
                deletes.append(existing_record)
        
        return {
            'inserts': inserts,
            'updates': updates,
            'deletes': deletes
        }
    
    def _load_existing_data(self, data_source: str) -> List[Dict]:
        """기존 데이터 로드"""
        query = """
        SELECT facility_id, public_api_id, name, address, facility_data, data_hash
        FROM facilities
        WHERE public_api_source = :source
        AND deleted_at IS NULL
        """
        
        return self.db.fetch_all(query, {"source": data_source})
    
    def _has_changed(self, existing: Dict, new: Dict) -> bool:
        """데이터 변경 여부 확인 (해시 비교)"""
        existing_hash = existing.get('data_hash')
        new_hash = self._calculate_hash(new)
        
        return existing_hash != new_hash
    
    def _calculate_hash(self, data: Dict) -> str:
        """데이터 해시 계산 (변경 감지용)"""
        # 일부 필드만 해시 계산 (메타데이터 제외)
        relevant_fields = {
            'name': data.get('name'),
            'address': data.get('address'),
            'capacity': data.get('capacity'),
            'grade': data.get('grade'),
            'facility_data': data.get('facility_data')
        }
        
        # JSON 정규화 후 해시
        normalized = json.dumps(relevant_fields, sort_keys=True, ensure_ascii=False)
        
        return hashlib.sha256(normalized.encode()).hexdigest()
```

---

## 3. 실시간 데이터 파이프라인

### 3.1 Apache Kafka 기반 스트리밍

```python
# data_pipeline/streaming/kafka_producer.py
from aiokafka import AIOKafkaProducer
import json
import logging

logger = logging.getLogger(__name__)

class FacilityEventProducer:
    """시설 이벤트 Kafka Producer"""
    
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
    
    async def start(self):
        """Producer 시작"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='gzip',
            acks='all',  # 모든 replica 확인
            retries=3
        )
        
        await self.producer.start()
        logger.info("Kafka producer started")
    
    async def stop(self):
        """Producer 종료"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send_facility_created(self, facility: Dict):
        """시설 생성 이벤트"""
        event = {
            'event_type': 'facility.created',
            'facility_id': facility['facility_id'],
            'facility_type': facility['facility_type'],
            'data': facility,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.producer.send(
            topic='facility-events',
            value=event,
            key=facility['facility_id'].encode('utf-8')
        )
        
        logger.info(f"Sent facility.created event: {facility['facility_id']}")
    
    async def send_facility_updated(self, facility: Dict, changes: Dict):
        """시설 수정 이벤트"""
        event = {
            'event_type': 'facility.updated',
            'facility_id': facility['facility_id'],
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.producer.send(
            topic='facility-events',
            value=event,
            key=facility['facility_id'].encode('utf-8')
        )
    
    async def send_review_created(self, review: Dict):
        """리뷰 작성 이벤트"""
        event = {
            'event_type': 'review.created',
            'review_id': review['review_id'],
            'facility_id': review['facility_id'],
            'rating': review['rating'],
            'timestamp': datetime.now().isoformat()
        }
        
        await self.producer.send(
            topic='review-events',
            value=event,
            key=review['facility_id'].encode('utf-8')
        )

# data_pipeline/streaming/kafka_consumer.py
from aiokafka import AIOKafkaConsumer
import asyncio

class FacilityEventConsumer:
    """시설 이벤트 Kafka Consumer"""
    
    def __init__(self, bootstrap_servers: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
    
    async def start(self):
        """Consumer 시작"""
        self.consumer = AIOKafkaConsumer(
            'facility-events',
            'review-events',
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            enable_auto_commit=False,  # 수동 커밋
            auto_offset_reset='earliest'
        )
        
        await self.consumer.start()
        logger.info("Kafka consumer started")
    
    async def stop(self):
        """Consumer 종료"""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def consume(self):
        """이벤트 소비"""
        try:
            async for message in self.consumer:
                event = message.value
                
                try:
                    # 이벤트 처리
                    await self.process_event(event)
                    
                    # 처리 완료 후 커밋
                    await self.consumer.commit()
                    
                except Exception as e:
                    logger.error(f"Event processing failed: {e}")
                    
                    # DLQ로 이동
                    await self.send_to_dlq(message)
                    
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise
    
    async def process_event(self, event: Dict):
        """이벤트 처리"""
        event_type = event['event_type']
        
        handlers = {
            'facility.created': self.handle_facility_created,
            'facility.updated': self.handle_facility_updated,
            'review.created': self.handle_review_created
        }
        
        handler = handlers.get(event_type)
        
        if handler:
            await handler(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    async def handle_facility_created(self, event: Dict):
        """시설 생성 이벤트 처리"""
        facility = event['data']
        
        # 1. Elasticsearch 인덱싱
        await index_to_elasticsearch(facility)
        
        # 2. 캐시 워밍
        await warm_cache(facility)
        
        # 3. 알림 발송 (주변 사용자)
        await notify_nearby_users(facility)
    
    async def handle_review_created(self, event: Dict):
        """리뷰 작성 이벤트 처리"""
        review = event
        
        # 1. 시설 평점 재계산
        await recalculate_facility_rating(review['facility_id'])
        
        # 2. 캐시 무효화
        await invalidate_facility_cache(review['facility_id'])
        
        # 3. 시설 운영자 알림
        await notify_facility_owner(review['facility_id'], review['review_id'])
```

---

## 4. 데이터 품질 관리

### 4.1 데이터 검증 프레임워크

```python
# data_pipeline/validators/data_validator.py
from typing import Dict, List, Tuple
import re
from datetime import datetime

class DataValidator:
    """데이터 품질 검증"""
    
    def validate_facility(self, facility: Dict) -> Tuple[bool, List[str]]:
        """시설 데이터 검증"""
        errors = []
        
        # 1. 필수 필드 체크
        required_fields = ['name', 'address', 'location', 'facility_type']
        
        for field in required_fields:
            if not facility.get(field):
                errors.append(f"Missing required field: {field}")
        
        # 2. 데이터 타입 검증
        if facility.get('capacity') and not isinstance(facility['capacity'], int):
            errors.append("capacity must be integer")
        
        if facility.get('rating') and not (0 <= facility['rating'] <= 5):
            errors.append("rating must be between 0 and 5")
        
        # 3. 포맷 검증
        if facility.get('phone'):
            if not self._validate_phone(facility['phone']):
                errors.append("Invalid phone format")
        
        if facility.get('email'):
            if not self._validate_email(facility['email']):
                errors.append("Invalid email format")
        
        # 4. 위치 정보 검증
        if facility.get('location'):
            if not self._validate_location(facility['location']):
                errors.append("Invalid location coordinates")
        
        # 5. 비즈니스 룰 검증
        if facility.get('facility_type') == 'childcare':
            if not facility.get('capacity'):
                errors.append("Childcare facility must have capacity")
        
        # 6. 데이터 일관성 체크
        if facility.get('current_occupancy') and facility.get('capacity'):
            if facility['current_occupancy'] > facility['capacity']:
                errors.append("Current occupancy exceeds capacity")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors
    
    def _validate_phone(self, phone: str) -> bool:
        """전화번호 검증"""
        pattern = r'^\d{2,3}-\d{3,4}-\d{4}$'
        return bool(re.match(pattern, phone))
    
    def _validate_email(self, email: str) -> bool:
        """이메일 검증"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))
    
    def _validate_location(self, location: Dict) -> bool:
        """위치 정보 검증 (서울시 범위)"""
        lat = location.get('lat')
        lng = location.get('lng')
        
        if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
            return False
        
        # 서울시 대략적 범위
        seoul_bounds = {
            'lat_min': 37.4,
            'lat_max': 37.7,
            'lng_min': 126.7,
            'lng_max': 127.2
        }
        
        return (
            seoul_bounds['lat_min'] <= lat <= seoul_bounds['lat_max'] and
            seoul_bounds['lng_min'] <= lng <= seoul_bounds['lng_max']
        )
    
    def calculate_quality_score(self, facility: Dict) -> float:
        """데이터 품질 점수 계산 (0-100)"""
        score = 0
        
        # 필수 필드 존재 (40점)
        required_fields = ['name', 'address', 'location', 'facility_type']
        filled_required = sum(1 for f in required_fields if facility.get(f))
        score += (filled_required / len(required_fields)) * 40
        
        # 선택 필드 존재 (30점)
        optional_fields = ['phone', 'email', 'website', 'description', 'photos']
        filled_optional = sum(1 for f in optional_fields if facility.get(f))
        score += (filled_optional / len(optional_fields)) * 30
        
        # 데이터 최신성 (20점)
        if facility.get('last_synced_at'):
            days_old = (datetime.now() - facility['last_synced_at']).days
            freshness_score = max(20 - days_old, 0)
            score += freshness_score
        
        # 데이터 정확성 (10점)
        # - 리뷰 수가 많을수록 정확성 높음
        review_count = facility.get('review_count', 0)
        accuracy_score = min(review_count / 10, 10)
        score += accuracy_score
        
        return min(score, 100)
```

### 4.2 데이터 품질 대시보드

```python
# data_pipeline/monitoring/quality_dashboard.py
class QualityDashboard:
    """데이터 품질 모니터링 대시보드"""
    
    async def get_quality_metrics(self) -> Dict:
        """데이터 품질 메트릭 수집"""
        
        # 1. 전체 시설 수
        total_facilities = await db.fetch_val(
            "SELECT COUNT(*) FROM facilities WHERE deleted_at IS NULL"
        )
        
        # 2. 완전성 (Completeness)
        completeness = await self._calculate_completeness()
        
        # 3. 정확성 (Accuracy)
        accuracy = await self._calculate_accuracy()
        
        # 4. 최신성 (Freshness)
        freshness = await self._calculate_freshness()
        
        # 5. 일관성 (Consistency)
        consistency = await self._calculate_consistency()
        
        # 6. 중복 (Duplicates)
        duplicates = await self._detect_duplicates()
        
        return {
            'total_facilities': total_facilities,
            'completeness': completeness,
            'accuracy': accuracy,
            'freshness': freshness,
            'consistency': consistency,
            'duplicates': duplicates,
            'overall_score': self._calculate_overall_score(
                completeness,
                accuracy,
                freshness,
                consistency
            )
        }
    
    async def _calculate_completeness(self) -> Dict:
        """완전성 계산"""
        query = """
        SELECT 
            COUNT(*) as total,
            COUNT(phone) as with_phone,
            COUNT(email) as with_email,
            COUNT(website) as with_website,
            COUNT(CASE WHEN JSONB_ARRAY_LENGTH(photos) > 0 THEN 1 END) as with_photos
        FROM facilities
        WHERE deleted_at IS NULL
        """
        
        result = await db.fetch_one(query)
        
        return {
            'phone_rate': result['with_phone'] / result['total'],
            'email_rate': result['with_email'] / result['total'],
            'website_rate': result['with_website'] / result['total'],
            'photos_rate': result['with_photos'] / result['total']
        }
    
    async def _calculate_freshness(self) -> Dict:
        """최신성 계산"""
        query = """
        SELECT 
            COUNT(*) FILTER (WHERE last_synced_at >= NOW() - INTERVAL '1 day') as last_24h,
            COUNT(*) FILTER (WHERE last_synced_at >= NOW() - INTERVAL '7 days') as last_7d,
            COUNT(*) FILTER (WHERE last_synced_at >= NOW() - INTERVAL '30 days') as last_30d,
            COUNT(*) as total
        FROM facilities
        WHERE deleted_at IS NULL
        """
        
        result = await db.fetch_one(query)
        
        return {
            'last_24h_rate': result['last_24h'] / result['total'],
            'last_7d_rate': result['last_7d'] / result['total'],
            'last_30d_rate': result['last_30d'] / result['total']
        }
```

---

이 문서는 데이터 파이프라인의 주요 개선 방안을 제시합니다. 다음으로 **시각적 아키텍처 다이어그램**과 **세분화가 필요한 기능**을 별도 문서로 작성하겠습니다.
