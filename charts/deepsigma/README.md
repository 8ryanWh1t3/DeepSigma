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

### Optional Toggles

- `configMap.enabled`: creates `<release>-config` from `configMap.data`
- `secret.enabled`: creates `<release>-secret` from `secret.stringData`
- `api.envFrom.*` / `dashboard.envFrom.*`: attach ConfigMap/Secret as env sources
- `fuseki.enabled`: deploy optional Fuseki StatefulSet + service
- `serviceMonitor.enabled`: emit Prometheus Operator `ServiceMonitor`

### Ingress Compatibility

Use `ingress.className` and `ingress.annotations` for controller-specific settings.

- NGINX example:
  - `ingress.className: nginx`
- Traefik example:
  - `ingress.className: traefik`
