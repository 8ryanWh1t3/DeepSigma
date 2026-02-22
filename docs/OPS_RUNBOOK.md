# Σ OVERWATCH — Ops Runbook

**Audience:** Operators, on-call engineers, CI maintainers
**Version:** v0.3.2
**SLO Reference:** [TEST_STRATEGY.md](TEST_STRATEGY.md) · [metrics/coherence_slos.md](metrics/coherence_slos.md)

---

## Quick Reference

| Task | Command |
|------|---------|
| Run Money Demo (recommended) | `make demo` |
| Run Money Demo (canonical) | `python -m coherence_ops.examples.drift_patch_cycle` |
| Score episodes | `python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json` |
| Run full test suite | `pytest tests/ -v` |
| Run with coverage | `pytest --cov=coherence_ops --cov-report=term-missing` |
| Validate schemas | `python tools/validate_examples.py` |
| Export Memory Graph | `python -m coherence_ops mg export ./coherence_ops/examples/sample_episodes.json --format=json` |
| IRIS: Why this decision? | `python -m coherence_ops iris query --type WHY --target ep-001` |
| Check artifact paths | `ls examples/episodes/ examples/drift/ coherence_ops/examples/` |

---

## 1. Running the Money Demo Reliably

The Money Demo is the canonical proof-of-life for the Drift → Patch loop.

### Single-Command Path

```bash
# From repo root with venv active:
make demo

# or canonical Python entrypoint:
python -m coherence_ops.examples.drift_patch_cycle
```

**Expected output:**

```
=== Money Demo: Drift → Patch Cycle ===
BASELINE  score=90.00  grade=A
DRIFT     score=85.75  grade=B   (freshness drift injected)
PATCH     score=90.00  grade=A   (drift resolved)
=== PASS ===
```

### Full Pipeline (step by step)

```bash
# 1. Validate episodes load cleanly
python tools/validate_examples.py

# 2. Run end-to-end seal → report
python -m coherence_ops.examples.e2e_seal_to_report

# 3. Score coherence
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json

# 4. Run Money Demo contract test
pytest tests/test_money_demo.py -v
```

### Good Output Indicators

- `BASELINE ... grade=A` — system is healthy
- `DRIFT ... grade=B` — drift correctly detected
- `PATCH ... grade=A` — patch correctly applied
- `=== PASS ===` — Money Demo contract met

---

## 2. Running Tests, Validating Schemas, and Verifying Artifacts

### Run Full Test Suite

```bash
pytest tests/ -v
```

14 test files covering all four artifacts (DLR, RS, DS, MG) plus integration, policy, schema, and demo contracts.

### Run With Coverage

```bash
pytest --cov=coherence_ops --cov-report=term-missing
```

### Run Individual Test Groups

```bash
# Core artifact tests
pytest tests/test_coherence_dlr.py tests/test_coherence_rs.py \
       tests/test_coherence_ds.py tests/test_coherence_mg.py -v

# Money Demo contract (critical — must always pass)
pytest tests/test_money_demo.py -v

# Integration (slower, exercises full pipeline)
pytest tests/test_integration.py -v
```

### Validate JSON Schemas

```bash
python tools/validate_examples.py
```

This validates all files under `examples/` against the JSON schemas in `specs/`.

**Expected:** `All examples valid.` or a count of files validated with zero errors.

### Verify LLM Data Model

```bash
python llm_data_model/05_validation/validate_examples.py
```

---

## 3. Logs and Diagnostics

### Where to Look

| Log Source | Location / Command |
|-----------|-------------------|
| Test output | Terminal / `pytest -v -s` |
| API server (when running) | `/tmp/deepsigma-api.log` or `uvicorn` stdout |
| Dashboard server | `dashboard/` — check Node console |
| OTel traces | Console stdout (if `OtelExporter` configured) |
| Python import errors | `python -c "import coherence_ops; print('ok')"` |

### What "Good" Looks Like

```
# Test suite passes
======================== 14 passed in X.XXs ========================

# Schema validation clean
Validated 4 episodes: OK
Validated 3 drift events: OK

# Coherence score healthy
{
  "overall": 90.0,
  "grade": "A",
  "dimensions": { ... }
}
```

### Reading Score Dimensions

| Dimension | Healthy | Degraded | Problem |
|-----------|---------|----------|---------|
| DLR coverage | ≥ 90 | 70–89 | < 70 |
| RS completeness | ≥ 80 | 60–79 | < 60 |
| DS resolution | ≥ 70 | 50–69 | < 50 |
| MG connectivity | ≥ 75 | 55–74 | < 55 |
| Overall | ≥ 80 (B) | 65–79 (C) | < 65 (D/F) |

---

## 4. Artifact Storage Expectations

| Artifact Type | Default Storage | Sample Path |
|--------------|----------------|-------------|
| Sealed episodes (input) | JSON files, `examples/episodes/` | `examples/episodes/01_success.json` |
| Sample episodes (coherence_ops) | `coherence_ops/examples/` | `coherence_ops/examples/sample_episodes.json` |
| Drift events | `examples/drift/` | `examples/drift/freshness_drift.json` |
| Demo drift | `coherence_ops/examples/` | `coherence_ops/examples/sample_drift.json` |
| Demo run outputs | `examples/demo-stack/drift_patch_cycle_run/` | See subdirectory |
| Memory Graph export | User-specified path | `--output ./mg_export.json` |

All persistent artifacts are plain JSON. No database is required for v0.3.x.

---

## 5. Incident Playbooks

---

### 5.1 WHY Retrieval > 60s (SLO Breach)

**SLO:** IRIS `WHY` query must complete in ≤ 60 seconds against the standard corpus.

**Symptoms:**
- `python -m coherence_ops iris query --type WHY --target <id>` hangs or exceeds 60s
- Dashboard IRIS panel shows timeout or spinner > 60s

**Triage steps (execute in order, stop when resolved):**

1. **Check episode count** — large corpora increase scan time:
   ```bash
   python -c "
   import json; from pathlib import Path
   eps = json.loads(Path('coherence_ops/examples/sample_episodes.json').read_text())
   print(f'{len(eps)} episodes in corpus')
   "
   ```
   If > 500 episodes: reduce corpus size or enable indexing (future feature).

2. **Check for schema validation errors** slowing the pipeline:
   ```bash
   python tools/validate_examples.py
   ```
   Fix any invalid episodes before retrying IRIS query.

3. **Check MG construction time** — Memory Graph is built in-memory on each query:
   ```bash
   time python -c "
   from coherence_ops import MemoryGraph
   import json; from pathlib import Path
   eps = json.loads(Path('coherence_ops/examples/sample_episodes.json').read_text())
   mg = MemoryGraph()
   for ep in eps: mg.add_episode(ep)
   print('MG built:', len(eps), 'episodes')
   "
   ```
   If > 10s: the corpus is too large for in-memory MG without optimization.

4. **Test the IRIS query in isolation:**
   ```bash
   time python -m coherence_ops iris query --type WHY --target ep-001
   ```

5. **Escalate** if all of the above pass but latency still exceeds 60s — file a GitHub issue with:
   - Output of `python -m coherence_ops score <path> --json`
   - Episode count
   - Python version (`python --version`)

**Resolution:** IRIS WHY query completes in ≤ 60s on the standard corpus (7 episodes). This is enforced in `tests/test_money_demo.py`.

---

### 5.2 Drift Detected But Patch Not Applied

**Symptoms:**
- Drift score shows `severity: red` or `yellow`
- Coherence score degraded (DS dimension < 50)
- `DRIFT` phase score drops but `PATCH` phase score does not recover

**Triage:**

1. **Confirm drift events exist and are valid:**
   ```bash
   python -c "
   import json; from pathlib import Path
   drifts = json.loads(Path('examples/drift/freshness_drift.json').read_text())
   print('Drift:', drifts.get('driftId'), 'severity:', drifts.get('severity'))
   "
   ```

2. **Check drift type is recognized:**
   Valid types: `time`, `freshness`, `fallback`, `bypass`, `verify`, `outcome`.
   Unknown types are silently mapped to `outcome`.

3. **Verify patch cycle runs:**
   ```bash
   python -m coherence_ops.examples.drift_patch_cycle
   ```
   The PATCH phase must restore score to within 2 points of BASELINE.

4. **Common causes:**
   - Drift `severity` field missing or wrong value (must be `green`/`yellow`/`red`)
   - Drift `episodeId` does not match any loaded episode → drift is orphaned
   - Patch type `recommendedPatchType` is empty → scorer cannot apply correction

5. **Fix:** Ensure drift JSON has correct `episodeId`, `severity`, and `recommendedPatchType`.

---

### 5.3 Schema Validation Failures

**Symptoms:**
- `python tools/validate_examples.py` exits non-zero
- `jsonschema.ValidationError` in test output
- CI fails on "Example validation" step

**Triage:**

1. **Identify the offending file:**
   ```bash
   python tools/validate_examples.py 2>&1 | grep -E "(FAIL|Error|error)"
   ```

2. **Get the specific validation error:**
   ```bash
   python -c "
   import json, jsonschema
   from pathlib import Path
   schema = json.loads(Path('specs/episode.schema.json').read_text())
   episode = json.loads(Path('examples/episodes/01_success.json').read_text())
   try:
       jsonschema.validate(episode, schema)
       print('Valid')
   except jsonschema.ValidationError as e:
       print('Field:', list(e.absolute_path))
       print('Error:', e.message)
   "
   ```

3. **Common causes:**
   - Missing required field (`episodeId`, `actor`, `outcome`, `seal`)
   - Wrong type: `timestamp` as string instead of integer
   - `outcome.code` value not in enum (`success`, `fail`, `partial`, `abstain`, `bypassed`)
   - `severity` not in enum (`green`, `yellow`, `red`)

4. **Fix:** Correct the offending field in the episode or drift JSON file.

5. **Verify fix:**
   ```bash
   python tools/validate_examples.py && echo "All valid"
   ```

---

## 6. Routine Operations Checklist

For each release or significant data update:

- [ ] `pytest tests/ -v` — all 14 test files pass
- [ ] `pytest tests/test_money_demo.py -v` — Money Demo contract passes
- [ ] `python tools/validate_examples.py` — all examples valid
- [ ] `python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json` — grade ≥ C
- [ ] IRIS WHY query completes in ≤ 60s
- [ ] No unresolved drift events in red severity

---

*See also: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) · [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [TEST_STRATEGY.md](TEST_STRATEGY.md)*
