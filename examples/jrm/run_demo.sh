#!/usr/bin/env bash
# JRM Demo — ingest, pipeline, validate for two environments.
#
# Usage:
#   bash examples/jrm/run_demo.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

DEMO_DIR="/tmp/jrm_demo_$$"
mkdir -p "$DEMO_DIR"

echo "=== JRM Demo ==="
echo ""

# Step 1: Generate demo data
echo "--- Step 1: Generate demo data ---"
python examples/jrm/generate_demo_data.py --output-dir "$DEMO_DIR"
echo ""

# Step 2: Ingest for SOC_EAST (Suricata)
echo "--- Step 2: Ingest Suricata → SOC_EAST ---"
python -m core.cli jrm ingest \
  --adapter suricata_eve \
  --in "$DEMO_DIR/suricata_demo.jsonl" \
  --out "$DEMO_DIR/norm_east.ndjson" \
  --env SOC_EAST \
  --json
echo ""

# Step 3: Ingest for SOC_WEST (Copilot)
echo "--- Step 3: Ingest Copilot → SOC_WEST ---"
python -m core.cli jrm ingest \
  --adapter copilot_agent \
  --in "$DEMO_DIR/copilot_demo.jsonl" \
  --out "$DEMO_DIR/norm_west.ndjson" \
  --env SOC_WEST \
  --json
echo ""

# Step 4: Run pipeline for SOC_EAST
echo "--- Step 4: Run pipeline → SOC_EAST packets ---"
mkdir -p "$DEMO_DIR/packets_east"
python -m core.cli jrm run \
  --in "$DEMO_DIR/norm_east.ndjson" \
  --env SOC_EAST \
  --packet-out "$DEMO_DIR/packets_east" \
  --json
echo ""

# Step 5: Run pipeline for SOC_WEST
echo "--- Step 5: Run pipeline → SOC_WEST packets ---"
mkdir -p "$DEMO_DIR/packets_west"
python -m core.cli jrm run \
  --in "$DEMO_DIR/norm_west.ndjson" \
  --env SOC_WEST \
  --packet-out "$DEMO_DIR/packets_west" \
  --json
echo ""

# Step 6: Validate all packets
echo "--- Step 6: Validate packets ---"
for zip in "$DEMO_DIR"/packets_east/*.zip "$DEMO_DIR"/packets_west/*.zip; do
  if [ -f "$zip" ]; then
    python -m core.cli jrm validate "$zip" --json
  fi
done
echo ""

echo "=== Demo complete ==="
echo "Artifacts in: $DEMO_DIR"
echo "  East packets: $DEMO_DIR/packets_east/"
echo "  West packets: $DEMO_DIR/packets_west/"
