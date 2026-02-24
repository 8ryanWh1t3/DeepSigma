#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/scale/docker-compose.scale.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for scale benchmark stack (not found in PATH)" >&2
  exit 127
fi

cleanup() {
  docker compose -f "$COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" up -d --build --scale api=3

for i in {1..30}; do
  if curl -fsS "http://localhost:18080/healthz" >/dev/null; then
    break
  fi
  sleep 1
  if [[ "$i" -eq 30 ]]; then
    echo "Proxy health check timed out" >&2
    exit 1
  fi
done

python "$ROOT_DIR/scripts/run_scale_benchmark.py" \
  --base-url "http://localhost:18080" \
  --path "/api/health" \
  --requests 100 \
  --concurrency 100 \
  --replicas 3 \
  --out-json "docs/examples/scale/report_latest.json" \
  --out-md "docs/examples/scale/report_latest.md"

echo "Scale benchmark completed."
