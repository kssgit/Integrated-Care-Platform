# Integrated Care Helm Chart

## Purpose

Deploy:

1. API service
2. Data pipeline monitoring service
3. ETL CronJob worker
4. API event consumer worker (optional)
5. API event DLQ retry worker (optional)
6. API event parking monitor worker (optional)

and optionally pull open-source platform dependencies through Helm dependency management.

## Optional Dependencies

1. PostgreSQL (`bitnami/postgresql`)
1. Redis (`bitnami/redis`)
2. Kafka (`bitnami/kafka`)
3. Prometheus stack (`prometheus-community/kube-prometheus-stack`)
4. Airflow (`apache-airflow/airflow`)

## Enable/Disable Dependencies

Configure in `values.yaml`:

```yaml
dependencies:
  postgresql:
    enabled: false
  redis:
    enabled: true
  kafka:
    enabled: true
  kubePrometheusStack:
    enabled: false
  airflow:
    enabled: false
```

## PostgreSQL Auto Wiring

If:

1. `dependencies.postgresql.enabled=true`
2. `secret.DATABASE_URL=""`

then `DATABASE_URL` is auto-generated from `postgresql.auth.*` values:

`postgresql://<username>:<password>@<release-name>-postgresql:5432/<database>`

## Redis/Kafka Auto Wiring

If:

1. `secret.REDIS_URL=""` and `dependencies.redis.enabled=true`
2. `secret.KAFKA_BOOTSTRAP_SERVERS=""` and `dependencies.kafka.enabled=true`

then these are auto-generated:

1. `REDIS_URL=redis://<release-name>-redis-master:6379/0`
2. `KAFKA_BOOTSTRAP_SERVERS=<release-name>-kafka:9092`

## Install

```bash
helm dependency update infra/helm/integrated-care
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace
```

## ETL CronJob

The chart deploys an ETL CronJob by default (`etlCronJob.enabled=true`).

Key values:

1. `etlCronJob.schedule`
2. `config.PIPELINE_START_PAGE`
3. `config.PIPELINE_END_PAGE`
4. `config.PIPELINE_OUTPUT_FILE`
5. `config.PIPELINE_STORE_BACKEND` (`jsonl` or `postgres`)
6. `config.PIPELINE_KAFKA_PUBLISH_ENABLED` (`true` or `false`)
7. `secret.DATABASE_URL` (required for `postgres`)
8. `secret.KAFKA_BOOTSTRAP_SERVERS` (required when Kafka publish enabled)
9. `config.API_CACHE_TTL_SECONDS` (API facility cache TTL)
10. `config.PIPELINE_API_EVENT_PUBLISH_ENABLED` (emit `etl_completed` to `api-events`)
11. `apiEventConsumer.enabled` (consume `api-events` and invalidate API cache)
12. `config.API_EVENT_CONSUMER_MAX_RETRIES` (consumer retry count before DLQ)
13. `config.API_EVENT_CONSUMER_BASE_DELAY_SECONDS` (retry backoff base seconds)
14. `config.API_EVENT_DLQ_TOPIC` (DLQ topic for failed events)
15. `config.API_EVENT_DEDUP_TTL_SECONDS` (dedup window by `trace_id`)
16. `apiEventDlqRetryWorker.enabled` (consume DLQ and replay to `api-events`)
17. `config.API_EVENT_DLQ_RETRY_MAX_ATTEMPTS` (max replay attempts)
18. `config.API_EVENT_PARKING_TOPIC` (final parking topic after retries)
19. `apiEventParkingMonitorWorker.enabled` (monitor parking topic)
20. `secret.PARKING_ALERT_WEBHOOK_URL` (webhook for parking alerts)
21. `config.PARKING_ALERT_THRESHOLD` (alert threshold per window)
22. `config.PARKING_ALERT_WINDOW_SECONDS` (window size in seconds)
23. `config.PARKING_ALERT_COOLDOWN_SECONDS` (minimum seconds between alerts)
24. `networkPolicy.enabled` (namespace-scoped network policy)
25. `api.pdb.enabled`, `api.pdb.minAvailable` (API disruption budget)
26. `pipelineMonitoring.pdb.enabled`, `pipelineMonitoring.pdb.minAvailable` (monitoring disruption budget)

## AKS Example

```bash
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace \
  -f infra/helm/integrated-care/values-aks.yaml
```

Override image tags at deploy time:

```bash
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace \
  -f infra/helm/integrated-care/values-aks.yaml \
  --set api.image.tag=<TAG> \
  --set pipelineMonitoring.image.tag=<TAG>
```
