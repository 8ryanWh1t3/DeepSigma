# DeepSigma Helm Chart

Deploys DeepSigma API and dashboard workloads to Kubernetes.

## Quickstart

```bash
helm install deepsigma ./charts/deepsigma
helm test deepsigma
```

## Workloads

- `api` Deployment + Service (`/api/health`, `/api/ready` probes)
- `dashboard` Deployment + Service (`/healthz` probes)
- Optional `fuseki` StatefulSet + Service (SPARQL endpoint on port `3030`)
- Optional Ingress with path routing:
  - `/` -> dashboard service
  - `/api` -> api service

## Values

- Base defaults: `values.yaml` (1 replica each, ingress disabled)
- Production overlay: `values-production.yaml` (3 replicas each, ingress enabled)

### Production Overlay

`values-production.yaml` enables:
- API autoscaling (`api.autoscaling.enabled=true`)
- ConfigMap + Secret env wiring for API/dashboard
- Fuseki and ServiceMonitor toggles
- Resource requests/limits for API and dashboard

### Resource Defaults (Production)

- API:
  - requests: `cpu=250m`, `memory=256Mi`
  - limits: `cpu=1`, `memory=512Mi`
- Dashboard:
  - requests: `cpu=150m`, `memory=192Mi`
  - limits: `cpu=500m`, `memory=512Mi`

### Replica Strategy (Persistence-backed mode)

- For local JSONL persistence (node-local storage), keep API single-writer semantics (`api.replicaCount=1`, HPA disabled).
- For shared/external persistence, use API HPA in production overlay (`min=3`, `max=10`).
- Fuseki remains optional and stateful with a PVC; scale API/dashboard independently from Fuseki data state.

### Optional Toggles

- `configMap.enabled`: creates `<release>-config` from `configMap.data`
- `secret.enabled`: creates `<release>-secret` from `secret.stringData`
- `dataPersistence.enabled`: creates/uses PVC for JSONL data directories (`/app/src/data`, `/app/data`)
- `api.envFrom.*` / `dashboard.envFrom.*`: attach ConfigMap/Secret as env sources
- `fuseki.enabled`: deploy optional Fuseki StatefulSet + service
- `serviceMonitor.enabled`: emit Prometheus Operator `ServiceMonitor`

### Persistence Notes

- By default, chart-managed JSONL PVC is disabled.
- To enable chart-managed PVC:
  - set `dataPersistence.enabled=true` and optionally `dataPersistence.storageClassName`.
- To use a pre-provisioned PVC:
  - set `dataPersistence.enabled=true` and `dataPersistence.existingClaim=<claim-name>`.
- For multi-replica API/dashboard, prefer shared RWX storage or external persistence backend.

### Ingress Compatibility

Use `ingress.className` and `ingress.annotations` for controller-specific settings.

- NGINX example:
  - `ingress.className: nginx`
- Traefik example:
  - `ingress.className: traefik`
