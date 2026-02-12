# Kubernetes/AKS Runbook

This runbook defines a baseline deployment flow for Kubernetes and AKS.

## Deployment Targets

1. API service (`python -m api`)
2. Data pipeline monitoring service (`python -m data_pipeline.monitoring`)
3. ETL CronJob (`python -m data_pipeline.jobs`)
4. API event consumer (`python -m api.event_consumer`)

## Manifest Location

Base manifests are under:

`infra/k8s/base`

Helm chart is under:

`infra/helm/integrated-care`

## Required Variables

1. `REDIS_URL`
2. `FACILITY_PROVIDER_BASE_URL`
3. `API_HOST`, `API_PORT`
4. `PIPELINE_MONITORING_HOST`, `PIPELINE_MONITORING_PORT`
5. `DATABASE_URL` (auto-generated when Helm PostgreSQL dependency is enabled and value is empty)

## Apply to Cluster

```bash
kubectl apply -k infra/k8s/base
```

## Helm Deployment (Recommended)

```bash
helm dependency update infra/helm/integrated-care
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace
```

AKS image override example:

```bash
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace \
  -f infra/helm/integrated-care/values-aks.yaml \
  --set api.image.tag=<TAG> \
  --set pipelineMonitoring.image.tag=<TAG>
```

AKS baseline override file:

`infra/helm/integrated-care/values-aks.yaml`

If you need to override repository at runtime:

```bash
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace \
  -f infra/helm/integrated-care/values-aks.yaml \
  --set api.image.repository=<ACR_LOGIN_SERVER>/integrated-care-api \
  --set pipelineMonitoring.image.repository=<ACR_LOGIN_SERVER>/integrated-care-pipeline \
  --set pipelineMonitoring.image.tag=<TAG>
```

## Probes and Metrics

1. Liveness: `/healthz`
2. Readiness: `/readyz`
3. Metrics: `/metrics`
4. API HPA: CPU target 65%, min 2, max 20

## AKS Notes

1. Replace placeholder images in deployment YAML files with your ACR image paths.
2. Use managed identity or Kubernetes secret integration for sensitive values.
3. If Prometheus Operator is not installed, remove `servicemonitor.yaml` from `kustomization.yaml`.
4. If you deploy via Helm, control OSS dependencies in `infra/helm/integrated-care/values.yaml`.
