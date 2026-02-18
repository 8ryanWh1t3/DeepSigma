# Σ OVERWATCH — Test Strategy

**Audience:** Engineers, CI maintainers, release managers
**Version:** v0.3.2
**See also:** [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [STABILITY.md](STABILITY.md)

---

## 1. Test Architecture Overview

The test suite lives in `tests/` and has three tiers:

| Tier | Files | Purpose |
|------|-------|---------|
| **Unit** | `test_coherence_*.py`, `test_degrade_ladder.py`, `test_policy_loader.py`, `test_prime.py`, `test_schema_claim.py`, `test_shacl_claim.py`, `test_api.py` | Isolate a single artifact or module |
| **Integration** | `test_integration.py` | Full DLR → RS → DS → MG → Scorer pipeline |
| **Contract** | `test_money_demo.py` | Money Demo SLO enforcement |

**Total:** 14 test files.

---

## 2. What Each Test File Covers

| File | What It Tests |
|------|--------------|
| `test_coherence_dlr.py` | DLRBuilder: episode ingestion, entry count, field mapping |
| `test_coherence_rs.py` | ReflectionSession: ingestion, summary generation, completeness |
| `test_coherence_ds.py` | DriftSignalCollector: drift ingestion, severity bucketing |
| `test_coherence_mg.py` | MemoryGraph: node/edge creation, episode linking, export |
| `test_coherence_bridge.py` | Bridge between coherence_ops and the engine layer |
| `test_degrade_ladder.py` | Degrade ladder: step selection, fallback chains |
| `test_policy_loader.py` | Policy pack YAML loading and contract resolution |
| `test_prime.py` | PRIME threshold gate: pass/fail conditions |
| `test_schema_claim.py` | Claim schema validation: required fields, enum values |
| `test_shacl_claim.py` | SHACL RDF shape validation on claims |
| `test_api.py` | coherence_ops public API: scorer, auditor, IRIS query interface |
| `test_integration.py` | End-to-end: episodes → all four artifacts → coherence report |
| `test_money_demo.py` | Money Demo contract: BASELINE A → DRIFT B → PATCH A |

---

## 3. SLOs Enforced by Tests

### Money Demo Contract (test_money_demo.py)

The following SLOs are enforced as hard assertions in the test suite:

| SLO | Assertion | Threshold |
|-----|-----------|-----------|
| Baseline grade | `grade == "A"` | Score ≥ 90 |
| Drift detection | `grade < "A"` | Score drops under freshness drift |
| Patch recovery | `grade == "A"` | Score restores to ≥ 90 after patch |

### WHY Retrieval Latency SLO (≤ 60 seconds)

**SLO:** An IRIS `WHY` query against the standard corpus must complete in ≤ 60 seconds.

This SLO is enforced in `tests/test_money_demo.py` or `tests/test_api.py`. To measure locally:

```bash
time python -m coherence_ops iris query --type WHY --target ep-001
```

Expected: completes in < 5 seconds on standard corpus (7 episodes). The 60s bound is a hard SLO ceiling for larger corpora.

If this SLO is breached:
1. Check corpus size (see [OPS_RUNBOOK.md §5.1](OPS_RUNBOOK.md))
2. File a GitHub issue tagged `performance`

---

## 4. What CI Currently Enforces

From `.github/workflows/ci.yml`:

### Test Job (matrix: Python 3.10, 3.11, 3.12)

```yaml
steps:
  - pip install -e ".[dev]"
  - pytest tests/test_coherence_dlr.py tests/test_coherence_rs.py ...  # unit
  - pytest tests/test_integration.py
  - python tools/validate_examples.py
  - python llm_data_model/05_validation/validate_examples.py
  - pytest tests/test_money_demo.py
```

**Enforced:** All unit tests, integration, example validation, Money Demo contract — across all three Python versions.

### Lint Job

```yaml
steps:
  - ruff check . (E, F, W rules; E501 ignored)
```

**Enforced:** No syntax errors, undefined names, or style violations.

### Dashboard Build Job

```yaml
steps:
  - npm install && npm run build
```

**Enforced:** TypeScript compiles cleanly.

---

## 5. Running Tests Locally

### Full suite

```bash
pytest tests/ -v
```

### With coverage

```bash
pytest --cov=coherence_ops --cov-report=term-missing
```

This reports line-by-line coverage for the `coherence_ops` package. Coverage report goes to terminal.

For HTML report:

```bash
pytest --cov=coherence_ops --cov-report=html
open htmlcov/index.html
```

### Individual tier

```bash
# Unit only
pytest tests/test_coherence_dlr.py tests/test_coherence_rs.py \
       tests/test_coherence_ds.py tests/test_coherence_mg.py -v

# Integration only
pytest tests/test_integration.py -v

# Money Demo contract only
pytest tests/test_money_demo.py -v
```

### Match CI exactly

```bash
# Install the same way CI does
pip install -e ".[dev]"

# Run the same commands CI runs
pytest tests/test_coherence_dlr.py tests/test_coherence_rs.py \
       tests/test_coherence_ds.py tests/test_coherence_mg.py \
       tests/test_coherence_bridge.py tests/test_prime.py \
       tests/test_schema_claim.py tests/test_api.py -v
pytest tests/test_integration.py -v
python tools/validate_examples.py
pytest tests/test_money_demo.py -v
```

---

## 6. Adding pytest-cov

`pytest-cov` is included in the dev dependencies as of v0.3.2.

To install:
```bash
pip install -e ".[dev]"    # includes pytest-cov
# or individually:
pip install pytest-cov
```

Coverage target (aspirational, not CI-gating):

| Package | Current estimate | Target (v0.4.x) |
|---------|-----------------|----------------|
| `coherence_ops` | ~60% | ≥ 80% |
| `engine` | ~40% | ≥ 60% |
| `adapters` | ~30% | ≥ 50% |

---

## 7. Next Milestones

| Milestone | Target Release | Description |
|-----------|---------------|-------------|
| Coverage gating (≥ 80% for coherence_ops) | v0.4.x | Add `--cov-fail-under=80` to CI |
| WHY latency benchmark test | v0.4.x | Automated assertion: IRIS WHY ≤ 60s |
| Adapter unit tests (MCP, OpenClaw, OTel) | v0.4.x | Isolated unit tests for each adapter |
| Schema round-trip tests | v0.4.x | Validate that all spec examples survive JSON round-trip |
| Load test (100+ episodes) | v0.5.x | Measure scorer and IRIS performance at scale |
| Property-based tests (hypothesis) | v1.0.x | Fuzz episode generation and schema validation |

---

*See also: [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [STABILITY.md](STABILITY.md) · [metrics/coherence_slos.md](metrics/coherence_slos.md)*
