# Mesh WAN Troubleshooting Guide

This runbook supports the WAN integration drill used by
`scripts/mesh_wan_partition.sh`.

## Testbed layout

- `mesh-a` -> `http://localhost:8111`
- `mesh-b` -> `http://localhost:8112`
- `mesh-c` -> `http://localhost:8113`
- Tenant ID: `tenant-wan`

## Common failures and fixes

1. Containers fail to build
- Symptom: `docker compose ... up --build` exits non-zero.
- Check: `docker compose -f docker/mesh/docker-compose.wan.yml logs`.
- Fix: verify Docker daemon is running and no stale image cache corruption (`docker builder prune`).

2. Node health never becomes ready
- Symptom: `curl /health` times out for one or more nodes.
- Check: container logs for import/runtime errors.
- Fix: rebuild from clean state:
  - `docker compose -f docker/mesh/docker-compose.wan.yml down -v`
  - `docker compose -f docker/mesh/docker-compose.wan.yml up -d --build`

3. Topology endpoint missing lag/state fields
- Symptom: `/mesh/{tenant}/topology` response lacks `replication_lag_s` or `state`.
- Check: node has replication events and status updates.
- Fix: POST seed events to `/mesh/{tenant}/{node}/push`, then retry topology endpoint.

4. Partition step does not isolate `mesh-c`
- Symptom: `mesh-c` remains reachable after `docker compose stop mesh-c`.
- Check: stale container from previous run.
- Fix: run full cleanup:
  - `docker compose -f docker/mesh/docker-compose.wan.yml down -v --remove-orphans`
  - rerun script.

5. Recovery step fails
- Symptom: `mesh-c` does not return healthy after `start`.
- Check: `docker compose ... logs mesh-c`.
- Fix: restart service with rebuild:
  - `docker compose -f docker/mesh/docker-compose.wan.yml up -d --build mesh-c`

## Manual verification commands

```bash
docker compose -f docker/mesh/docker-compose.wan.yml up -d --build
curl -s http://localhost:8111/mesh/tenant-wan/topology | python -m json.tool
docker compose -f docker/mesh/docker-compose.wan.yml stop mesh-c
curl -sSf http://localhost:8113/health   # expected to fail while partitioned
docker compose -f docker/mesh/docker-compose.wan.yml start mesh-c
curl -sSf http://localhost:8113/health   # expected to pass after recovery
```
