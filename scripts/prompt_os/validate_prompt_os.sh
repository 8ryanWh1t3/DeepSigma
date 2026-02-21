#!/usr/bin/env bash
# Run the Prompt OS v2 CSV ↔ Schema validator.
# Exit code mirrors the Python script: 0 = pass, 1 = fail.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

python3 "$SCRIPT_DIR/validate_prompt_os.py" \
  --csv-dir "$REPO_ROOT/sample_data/prompt_os_v2" \
  --schema  "$REPO_ROOT/schemas/prompt_os/prompt_os_schema_v2.json" \
  "$@"
