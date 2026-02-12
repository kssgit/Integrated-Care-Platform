# Feature TODO

This file tracks functional development status.

## In Progress

1. `trust-safety`: resident verification module (dong/geofence based)
2. `trust-safety`: OCR receipt verification pipeline baseline
3. `trust-safety`: robots policy validator for review ingestion

## Todo

1. `geo-engine`: route-risk scoring model and PostGIS integration adapter
2. `trust-safety`: safe-number routing adapter (050 relay)
3. `apps/api`: trust-safety API endpoints (router/service/repository split)
4. `apps/api`: geo-engine API endpoints and caching strategy tuning
5. `data-pipeline`: provider expansion (Gyeonggi/National adapters)
6. `data-pipeline`: ETL load path to production DB and quality checks
7. `apps/web`: MVP integration screens for search, comparison, inquiry, review

## Done

1. API boundary layer (rate limit, circuit breaker, response schema)
2. Data-pipeline ETL skeleton and provider retry/concurrency controls
3. Kafka event flow (normalized, errors, DLQ, retry handler)
4. API event consumer, DLQ retry worker, parking monitor worker
5. Helm chart with optional OSS dependencies and AKS overrides
6. Observability baseline (`/metrics`, tracing, ETL metrics exporter)
7. `geo-engine` core calculations (distance, geofence, golden-time baseline)
