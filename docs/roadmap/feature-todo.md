# Feature TODO

This file tracks functional development status.

## In Progress

1. None

## Todo

1. `apps/web`: MVP integration screens for search, comparison, inquiry, review

## Done

1. API boundary layer (rate limit, circuit breaker, response schema)
2. Data-pipeline ETL skeleton and provider retry/concurrency controls
3. Kafka event flow (normalized, errors, DLQ, retry handler)
4. API event consumer, DLQ retry worker, parking monitor worker
5. Helm chart with optional OSS dependencies and AKS overrides
6. Observability baseline (`/metrics`, tracing, ETL metrics exporter)
7. `geo-engine` core calculations (distance, geofence, golden-time baseline)
8. `trust-safety` baseline modules (resident verification, OCR receipt validation, robots policy)
9. `trust-safety` safe-number routing adapter (050 relay)
10. `apps/api` trust-safety API endpoint for safe-number routing
11. `apps/api` geo-engine API endpoints (`distance`, `geofence`, `golden-time`) with cache integration
12. `data-pipeline` provider expansion (`Gyeonggi/National` adapters, provider routing path)
13. `data-pipeline` ETL production DB load hardening (batched upsert) and quality checks (reject ratio gate)
14. `geo-engine` route-risk scoring model and PostGIS integration adapter
