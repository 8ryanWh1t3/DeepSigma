#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker/mesh/docker-compose.wan.yml"
TENANT="tenant-wan"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/6] Building and starting 3-node WAN mesh testbed..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[2/6] Waiting for node health endpoints..."
for port in 8111 8112 8113; do
  for i in {1..20}; do
    if curl -fsS "http://localhost:${port}/health" >/dev/null; then
      break
    fi
    sleep 1
    if [[ "$i" == "20" ]]; then
      echo "Node on port ${port} did not become healthy" >&2
      exit 1
    fi
  done
done

echo "[3/6] Seeding replication activity..."
curl -fsS -X POST "http://localhost:8111/mesh/${TENANT}/edge-A/push" \
  -H "Content-Type: application/json" \
  -d '{"envelopes":[{"id":"wan-e1","timestamp":"2026-02-23T00:00:00Z"}]}' >/dev/null
curl -fsS -X POST "http://localhost:8112/mesh/${TENANT}/validator-B/push" \
  -H "Content-Type: application/json" \
  -d '{"envelopes":[{"id":"wan-e2","timestamp":"2026-02-23T00:00:01Z"}]}' >/dev/null

echo "[4/6] Verifying topology visibility API..."
TOPOLOGY_JSON="$(curl -fsS "http://localhost:8111/mesh/${TENANT}/topology")"
python - <<'PY' "$TOPOLOGY_JSON"
import json, sys
obj = json.loads(sys.argv[1])
assert obj["node_count"] >= 3, obj
nodes = obj["nodes"]
assert any("replication_lag_s" in n for n in nodes), obj
assert any("state" in n for n in nodes), obj
print("Topology API verified")
PY

echo "[5/6] Inducing partition by stopping mesh-c..."
docker compose -f "$COMPOSE_FILE" stop mesh-c
sleep 2
if curl -fsS "http://localhost:8113/health" >/dev/null; then
  echo "Expected mesh-c to be unreachable after partition, but health still responds" >&2
  exit 1
fi
echo "Partition verified: mesh-c unreachable"

echo "[6/6] Recovering partition..."
docker compose -f "$COMPOSE_FILE" start mesh-c
for i in {1..20}; do
  if curl -fsS "http://localhost:8113/health" >/dev/null; then
    echo "Recovery verified: mesh-c reachable"
    exit 0
  fi
  sleep 1
done
echo "mesh-c did not recover in time" >&2
exit 1
