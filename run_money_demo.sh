#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$ROOT_DIR/docs/examples/demo-stack/drift_patch_cycle_run"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

step() {
  printf "\n[%s] %s\n" "$1" "$2"
}

step "1/3" "Running Money Demo (Drift -> Patch cycle)"
python -m coherence_ops.examples.drift_patch_cycle

step "2/3" "Verifying demo contract"
python -m pytest tests/test_money_demo.py -q

step "3/3" "Done"
echo "Artifacts: $OUTPUT_DIR"
echo "Evidence:  $ROOT_DIR/docs/examples/demo-stack/MONEY_DEMO_EVIDENCE.md"

if command -v open >/dev/null 2>&1; then
  open "$OUTPUT_DIR" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$OUTPUT_DIR" >/dev/null 2>&1 || true
fi
