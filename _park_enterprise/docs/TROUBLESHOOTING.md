# Σ OVERWATCH — Troubleshooting Guide

**Audience:** Operators, developers, CI engineers
**See also:** [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)

Each entry follows: **Symptom → Likely Cause → Fix → Verify**

---

## Python Environment Issues

### 1. `ModuleNotFoundError: No module named 'coherence_ops'`

**Symptom:** Any `python -m coherence_ops ...` command fails with import error.

**Cause:** Package not installed or virtual environment not active.

**Fix:**
```bash
# Activate venv first
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install package
pip install -e .
```

**Verify:**
```bash
python -c "import coherence_ops; print('OK')"
```

---

### 2. `SyntaxError` or `TypeError` on import

**Symptom:** Import of `coherence_ops` raises a syntax or type error immediately.

**Cause:** Python version < 3.10 (uses `match`, `|` union types, etc.).

**Fix:**
```bash
python --version          # Must be 3.10+
pyenv install 3.11.9      # Install if needed
pyenv local 3.11.9
pip install -e .
```

**Verify:**
```bash
python --version && python -c "import coherence_ops; print('OK')"
```

---

### 3. `pip install -e .` fails with setuptools error

**Symptom:** Error like `AttributeError: install_requires` or `egg_info` failure.

**Cause:** Outdated pip or setuptools.

**Fix:**
```bash
pip install --upgrade pip setuptools wheel
pip install -e .
```

**Verify:**
```bash
pip show deepsigma
```

---

## Missing Dependencies

### 4. `ModuleNotFoundError: No module named 'jsonschema'`

**Symptom:** Schema validation fails at import.

**Cause:** Core dependencies not installed.

**Fix:**
```bash
pip install -r requirements.txt
# or:
pip install jsonschema "referencing>=0.35.0" "pyyaml>=6.0"
```

**Verify:**
```bash
python -c "import jsonschema; print(jsonschema.__version__)"
```

---

### 5. `ModuleNotFoundError: No module named 'opentelemetry'`

**Symptom:** `OtelExporter` raises ImportError (but as a warning, not a crash).

**Cause:** Optional OpenTelemetry packages not installed. The adapter gracefully degrades without them.

**Fix** (only if you need OTEL tracing):
```bash
pip install "opentelemetry-api>=1.20.0" "opentelemetry-sdk>=1.20.0" \
            "opentelemetry-exporter-otlp>=1.20.0"
# or:
pip install -e ".[otel]"
```

**Verify:**
```bash
python -c "from opentelemetry import trace; print('OTEL OK')"
```

---

## Test Failures

### 6. `pytest: command not found`

**Symptom:** Running `pytest` fails — command not found.

**Cause:** Dev dependencies not installed.

**Fix:**
```bash
pip install -e ".[dev]"
```

**Verify:**
```bash
pytest --version
```

---

### 7. Tests fail with `FileNotFoundError` on episode or drift JSON

**Symptom:** Test raises `FileNotFoundError` for a path under `examples/` or `coherence_ops/examples/`.

**Cause:** Tests run from wrong directory, or sample files missing.

**Fix:**
```bash
# Always run pytest from repo root
cd /path/to/DeepSigma
pytest tests/ -v

# Confirm sample files exist
ls examples/episodes/ coherence_ops/examples/
```

**Verify:**
```bash
pytest tests/test_coherence_dlr.py -v
```

---

### 8. `test_money_demo.py` fails — score doesn't reach grade A after patch

**Symptom:** Money Demo test fails with assertion like `expected grade A, got B`.

**Cause:** Episode data drift or scorer weights changed from expected baseline.

**Fix:**
```bash
# Run interactively to see raw scores
python -m coherence_ops.examples.drift_patch_cycle

# Check if sample episodes are intact
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json
```

If sample data was modified, restore from git: `git checkout coherence_ops/examples/`.

**Verify:**
```bash
pytest tests/test_money_demo.py -v
```

---

## JSON Schema Errors

### 9. `jsonschema.ValidationError` on episode load

**Symptom:** `validate_examples.py` fails or coherence score raises validation error.

**Cause:** Episode JSON is missing a required field or has wrong type.

**Fix:**
```bash
# Identify which field fails
python -c "
import json, jsonschema
from pathlib import Path
schema = json.loads(Path('specs/episode.schema.json').read_text())
ep = json.loads(Path('examples/episodes/01_success.json').read_text())
jsonschema.validate(ep, schema)
print('Valid')
"
```

Required top-level fields: `episodeId`, `actor`, `outcome`, `seal`.

`outcome.code` must be one of: `success`, `fail`, `partial`, `abstain`, `bypassed`.

**Verify:**
```bash
python tools/validate_examples.py && echo "All valid"
```

---

### 10. `referencing.exceptions.Unresolvable` on schema load

**Symptom:** Schema validation crashes with `Unresolvable` reference error.

**Cause:** `referencing` package version < 0.35.0, or `$ref` path is broken.

**Fix:**
```bash
pip install "referencing>=0.35.0"
```

**Verify:**
```bash
python tools/validate_examples.py
```

---

## YAML Issues

### 11. `yaml.parser.ParserError` when loading policy pack

**Symptom:** Policy pack YAML fails to parse.

**Cause:** Indentation error, tab character instead of spaces, or YAML syntax error.

**Fix:** Open the policy pack file and check for:
- Mixed tabs and spaces (use spaces only)
- Unquoted strings containing `:` characters
- Duplicate keys

```bash
python -c "
import yaml
from pathlib import Path
data = yaml.safe_load(Path('your_policy_pack.yaml').read_text())
print('YAML OK:', list(data.keys()))
"
```

**Verify:** Re-run the command that failed with the YAML.

---

## Path and Permission Issues

### 12. `PermissionError` when writing export files

**Symptom:** Memory Graph export or demo output fails with `PermissionError`.

**Cause:** Target directory is not writable.

**Fix:**
```bash
# Write to a temp directory
python -m coherence_ops mg export ./coherence_ops/examples/sample_episodes.json \
    --format=json --output /tmp/mg_export.json
```

**Verify:**
```bash
ls -la /tmp/mg_export.json
```

---

### 13. `FileNotFoundError` for `tool_catalog.json` in MCP scaffold

**Symptom:** `python adapters/mcp/mcp_server_scaffold.py` fails to start.

**Cause:** Script run from wrong directory (uses relative path resolution).

**Fix:**
```bash
# Always run from repo root — the script resolves REPO_ROOT itself
cd /path/to/DeepSigma
python adapters/mcp/mcp_server_scaffold.py
```

**Verify:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python adapters/mcp/mcp_server_scaffold.py
```

---

## Demo and CLI

### 14. `python -m coherence_ops.examples.drift_patch_cycle` — `ModuleNotFoundError`

**Symptom:** Module not found when running demo examples.

**Cause:** Package not installed in editable mode, or examples not on PYTHONPATH.

**Fix:**
```bash
pip install -e .
python -m coherence_ops.examples.drift_patch_cycle
```

**Verify:** Output shows `BASELINE ... DRIFT ... PATCH ... PASS`.

---

### 15. `coherence` CLI command not found

**Symptom:** `coherence score ...` gives "command not found".

**Cause:** `pip install -e .` not run, so entry points aren't registered.

**Fix:**
```bash
pip install -e .
# Now use: coherence score ./coherence_ops/examples/sample_episodes.json
# Or always use: python -m coherence_ops score ...
```

**Verify:**
```bash
coherence --help
```

---

### 16. IRIS query returns empty results

**Symptom:** `python -m coherence_ops iris query --type WHY --target ep-001` returns no data.

**Cause:** Episode ID doesn't match any loaded episode, or corpus path is wrong.

**Fix:**
```bash
# Check what episode IDs are available
python -c "
import json; from pathlib import Path
eps = json.loads(Path('coherence_ops/examples/sample_episodes.json').read_text())
for ep in eps: print(ep.get('episodeId'))
"
# Then use a real ID:
python -m coherence_ops iris query --type WHY --target <real-id>
```

**Verify:** Response contains `summary` and `data` fields.

---

## Environment Variables

### 17. Missing `OTEL_EXPORTER_OTLP_ENDPOINT` — traces not appearing

**Symptom:** OTel configured but spans not reaching Jaeger/Tempo/Honeycomb.

**Cause:** Endpoint env var not set. Default is console output only.

**Fix:**
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="sigma-overwatch"
# Then run your demo or test
```

**Verify:** Check your OTel backend for incoming spans from service `sigma-overwatch`.

---

### 18. `ANTHROPIC_API_KEY` not set (LangChain integration)

**Symptom:** LangChain demos fail with authentication error.

**Cause:** API key env var missing.

**Fix:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Verify:**
```bash
python -c "import os; assert os.environ.get('ANTHROPIC_API_KEY'), 'Not set'"
```

---

## CI Failures

### 19. CI fails on `ruff` lint step

**Symptom:** GitHub Actions lint job fails with style errors.

**Cause:** New code introduced E/F/W violations (E501 line-length is ignored).

**Fix:**
```bash
# Run lint locally
ruff check .

# Auto-fix where possible
ruff check . --fix
```

**Verify:**
```bash
ruff check . && echo "Lint clean"
```

---

### 20. Dashboard build fails in CI (`npm run build` error)

**Symptom:** CI "dashboard-build" job fails with TypeScript or build errors.

**Cause:** TypeScript type errors introduced in `dashboard/src/`, or missing `node_modules`.

**Fix:**
```bash
cd dashboard
npm install
npm run build
```

Check the error: TypeScript type errors are usually in `App.tsx` or `mockData.ts`.

**Verify:**
```bash
cd dashboard && npm run build && echo "Build OK"
```

---

*See also: [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [TEST_STRATEGY.md](TEST_STRATEGY.md)*
