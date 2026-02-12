# Integrated Care Helm Chart

## Purpose

Deploy:

1. API service
2. Data pipeline monitoring service

and optionally pull open-source platform dependencies through Helm dependency management.

## Optional Dependencies

1. Redis (`bitnami/redis`)
2. Kafka (`bitnami/kafka`)
3. Prometheus stack (`prometheus-community/kube-prometheus-stack`)
4. Airflow (`apache-airflow/airflow`)

## Enable/Disable Dependencies

Configure in `values.yaml`:

```yaml
dependencies:
  redis:
    enabled: true
  kafka:
    enabled: true
  kubePrometheusStack:
    enabled: false
  airflow:
    enabled: false
```

## Install

```bash
helm dependency update infra/helm/integrated-care
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace
```

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
