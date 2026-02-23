# Helm Deployment and Validation

This document defines the install/test path for issue #190.

## Chart location

- `charts/deepsigma`

## Local install path (kind)

```bash
kind create cluster --name deepsigma
helm upgrade --install deepsigma charts/deepsigma --namespace deepsigma --create-namespace
kubectl -n deepsigma rollout status deploy/deepsigma --timeout=180s
helm test deepsigma -n deepsigma
```

## Local install path (minikube)

```bash
minikube start
helm upgrade --install deepsigma charts/deepsigma --namespace deepsigma --create-namespace
kubectl -n deepsigma rollout status deploy/deepsigma --timeout=180s
helm test deepsigma -n deepsigma
```

## Diagnostics when install/test fails

```bash
kubectl get pods -n deepsigma -o wide
kubectl describe deploy deepsigma -n deepsigma
kubectl logs deploy/deepsigma -n deepsigma --all-containers=true --tail=200
kubectl get events -n deepsigma --sort-by=.metadata.creationTimestamp | tail -n 50
helm get all deepsigma -n deepsigma
```

## CI coverage

- `helm lint` and `helm template` render checks
- kind cluster install smoke path
- `helm test` smoke checks
