# Trust Scorecard v1.0

**Status:** Normative
**Version:** 1.0.0
**Since:** v0.6.0

---

## Overview

The Trust Scorecard is a single JSON artifact that captures measurable trust metrics from a Golden Path run or production deployment. It answers: **"How trustworthy is this system right now?"**

The scorecard is:
- **Generated** by `tools/trust_scorecard.py` from Golden Path output artifacts
- **Emitted** by CI on every push/PR as a build artifact
- **Surfaced** in the dashboard via a minimal panel
- **Deterministic** when run against fixture data

---

## Metrics

| Metric | Type | Source | SLO Target |
|--------|------|--------|------------|
| `iris_why_latency_ms` | float | Step 7 timing | p95 ≤ 60,000ms |
| `drift_detect_latency_ms` | float | Step 5 timing | p95 ≤ 5,000ms |
| `patch_latency_ms` | float | Step 6 timing | p95 ≤ 5,000ms |
| `connector_ingest_records_per_sec` | float | Step 1 records / time | ≥ 10 rec/s |
| `schema_validation_failures` | int | Schema errors across all steps | 0 |
| `total_elapsed_ms` | float | End-to-end pipeline time | ≤ 120,000ms |
| `steps_completed` | int | Steps completed (out of 7) | 7 |
| `steps_total` | int | Total steps expected | 7 |
| `all_steps_passed` | bool | All 7 steps completed | true |
| `drift_events_detected` | int | Drift events from step 5 | ≥ 1 (for fixture data) |
| `patch_applied` | bool | Step 6 applied a patch | true |
| `iris_queries_resolved` | int | IRIS queries with RESOLVED status | 3 |
| `baseline_score` | float | Coherence score before drift | > 0 |
| `baseline_grade` | str | Coherence grade before drift | A-F |
| `patched_score` | float | Coherence score after patch | > 0 |
| `patched_grade` | str | Coherence grade after patch | A-F |
| `coverage_pct` | float or null | Test coverage if available | ≥ 80% |
| `timestamp` | str | ISO-8601 generation time | — |

---

## JSON Output

```json
{
  "scorecard_version": "1.0",
  "timestamp": "2026-02-18T12:00:00Z",
  "source_dir": "golden_path_ci_out",
  "metrics": {
    "iris_why_latency_ms": 45.2,
    "drift_detect_latency_ms": 12.5,
    "patch_latency_ms": 8.3,
    "connector_ingest_records_per_sec": 125.0,
    "schema_validation_failures": 0,
    "total_elapsed_ms": 180.5,
    "steps_completed": 7,
    "steps_total": 7,
    "all_steps_passed": true,
    "drift_events_detected": 5,
    "patch_applied": true,
    "iris_queries_resolved": 3,
    "baseline_score": 87.5,
    "baseline_grade": "B",
    "patched_score": 90.0,
    "patched_grade": "A",
    "coverage_pct": null
  },
  "slo_checks": {
    "iris_why_latency_ok": true,
    "all_steps_passed": true,
    "schema_clean": true,
    "score_positive": true
  }
}
```

---

## Generation

```bash
# From Golden Path output directory
python -m tools.trust_scorecard --input golden_path_ci_out --output trust_scorecard.json

# With coverage (if available)
python -m tools.trust_scorecard --input golden_path_ci_out --output trust_scorecard.json --coverage 85.3
```

---

## CI Integration

The scorecard is generated after the Golden Path fixture gate in CI:

```yaml
- name: Generate Trust Scorecard
  run: |
    python -m tools.trust_scorecard --input golden_path_ci_out --output trust_scorecard.json
    cat trust_scorecard.json
```

---

## Dashboard Panel

The Trust Scorecard panel in the dashboard reads `trust_scorecard.json` and displays:
- Steps completed (7/7)
- Baseline → Patched score
- IRIS resolution status
- SLO check summary (green/red)
