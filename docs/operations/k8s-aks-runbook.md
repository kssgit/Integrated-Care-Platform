# Kubernetes/AKS Runbook

## 목표
- Dev에서 pipeline/admin e2e를 먼저 검증하고, Prod는 승인 전 준비 상태를 보장한다.

## Helm 배포 파일
- 기본: `infra/helm/integrated-care/values.yaml`
- Dev 모드: `infra/helm/integrated-care/values-mode-dev.yaml`
- Prod 모드: `infra/helm/integrated-care/values-mode-prod.yaml`
- AKS 오버레이: `infra/helm/integrated-care/values-aks.yaml`
- 로컬 프라이빗: `infra/helm/integrated-care/values-local-private.yaml`

## Preflight Checklist
- [ ] Namespace/SA/RBAC 준비 완료
- [ ] `DATABASE_URL`, `REDIS_URL`, `KAFKA_BOOTSTRAP_SERVERS` 유효
- [ ] `AIRFLOW_API_*` 시크릿 값 유효
- [ ] 스토리지 클래스(`jonathan-system-sc` 또는 AKS 클래스) 존재
- [ ] Kafka 토픽 생성/권한 확인
- [ ] 이미지 pull secret 유효

## Dev 배포
```bash
helm dependency update infra/helm/integrated-care
helm upgrade --install integrated-care infra/helm/integrated-care \
  --namespace integrated-care --create-namespace \
  -f infra/helm/integrated-care/values.yaml \
  -f infra/helm/integrated-care/values-mode-dev.yaml \
  -f infra/helm/integrated-care/values-local-private.yaml
```

## Prod 준비 배포(검증용)
```bash
helm dependency update infra/helm/integrated-care
helm lint infra/helm/integrated-care
helm template integrated-care infra/helm/integrated-care \
  -f infra/helm/integrated-care/values.yaml \
  -f infra/helm/integrated-care/values-mode-prod.yaml \
  -f infra/helm/integrated-care/values-aks.yaml > /tmp/integrated-care-prod-rendered.yaml
```

## Dev E2E Smoke
1. 파드/잡 상태
```bash
kubectl -n integrated-care get pods
kubectl -n integrated-care get jobs
```

2. Admin trigger → Airflow run
- `POST /v1/admin/pipeline/runs`
- `GET /v1/admin/pipeline/runs/{dag_run_id}`

3. Pipeline 결과 확인
- Postgres 적재 row 증가
- API 조회 결과 반영
- `/metrics`에 아래 지표 노출
  - `pipeline_run_total{provider,status}`
  - `pipeline_records_total{provider,result}`
  - `pipeline_reject_ratio{provider}`
  - `pipeline_duration_seconds{provider}`
  - `pipeline_provider_http_errors_total{provider,code}`

4. 실패 복구
- provider 5xx 유도 후 재시도/실패 로그 확인
- admin retry endpoint로 재실행 성공 확인

## Prod 승인 게이트
- [ ] `helm lint` 통과
- [ ] `helm template` 렌더링 오류 없음
- [ ] migration dry-run 로그 확인
- [ ] smoke checklist 100% 완료
- [ ] rollback revision 확인 및 실행 절차 점검

## 장애 대응 표준
1. 증상: trigger 실패
- 원인: Airflow 인증/네트워크 오류
- 조치: `AIRFLOW_API_*` 시크릿 확인, admin-service 로그 점검

2. 증상: run 실패(reject ratio 초과)
- 원인: 공급자 payload 품질 저하
- 조치: provider 응답 샘플 확인, threshold/정규화 규칙 점검

3. 증상: 저장 성공 후 이벤트 발행 실패
- 원인: Kafka 연결/권한 문제
- 조치: 브로커 상태 확인, topic ACL 확인, 재실행 정책 적용
