# Feature TODO

This file tracks functional development status.

## In Progress

1. `trust-safety`: safe-number routing adapter (050 relay)
2. `apps/api`: trust-safety API endpoints (router/service/repository split)
3. `geo-engine`: route-risk scoring model and PostGIS integration adapter

## Todo

1. `apps/api`: geo-engine API endpoints and caching strategy tuning
2. `data-pipeline`: provider expansion (Gyeonggi/National adapters)
3. `data-pipeline`: ETL load path to production DB and quality checks
4. `apps/web`: MVP integration screens for search, comparison, inquiry, review

## Done

1. API boundary layer (rate limit, circuit breaker, response schema)
2. Data-pipeline ETL skeleton and provider retry/concurrency controls
3. Kafka event flow (normalized, errors, DLQ, retry handler)
4. API event consumer, DLQ retry worker, parking monitor worker
5. Helm chart with optional OSS dependencies and AKS overrides
6. Observability baseline (`/metrics`, tracing, ETL metrics exporter)
7. `geo-engine` core calculations (distance, geofence, golden-time baseline)
8. `trust-safety` baseline modules (resident verification, OCR receipt validation, robots policy)
