# Stateless API Scale Guide

This guide provides a reproducible benchmark path for issue #197:

- 3 API replicas behind a reverse proxy
- 100 concurrent requests
- Throughput + latency report capture

## 1) Start 3-replica benchmark stack

```bash
bash scripts/run_scale_stack.sh
```

This command:
- builds and launches `api` and `proxy` from `docker/scale/docker-compose.scale.yml`
- scales `api` to 3 replicas
- runs a 100-concurrency benchmark against `http://localhost:18080/api/health`
- writes benchmark outputs:
  - `docs/examples/scale/report_latest.json`
  - `docs/examples/scale/report_latest.md`

## 2) Run benchmark manually (optional)

```bash
docker compose -f docker/scale/docker-compose.scale.yml up -d --build --scale api=3
python scripts/run_scale_benchmark.py \
  --base-url http://localhost:18080 \
  --path /api/health \
  --requests 100 \
  --concurrency 100 \
  --replicas 3
```

## 3) Interpret results

Acceptance criteria for #197:
- 3-replica benchmark behind reverse proxy: PASS when `--replicas 3`
- 100-concurrent-request scenario: PASS when `--concurrency >= 100`
- Zero functional errors: PASS when `error_count == 0`
- Throughput/latency report captured: PASS when both report files exist

## Replica sizing guidance

- **Pilot baseline (small team / low QPS):** 2 replicas, concurrency 50
- **Current target profile:** 3 replicas, concurrency 100
- **Burst profile:** 5 replicas when p95 latency exceeds target for sustained periods

Practical rule:
- If p95 latency rises >2x baseline for 3 consecutive runs, increase replicas by +2.
- If p95 remains stable and CPU is under 40%, reduce by -1 replica to save cost.

## Operational notes

- Keep API workers at 1 per container for predictable request-scoped state behavior.
- Scale horizontally with container replicas, not process workers.
- Re-run benchmark after major schema, storage, or policy changes.
