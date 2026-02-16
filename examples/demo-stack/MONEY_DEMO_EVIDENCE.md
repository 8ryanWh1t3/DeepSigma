# Money Demo Evidence — v0.3 Drift → Patch Cycle

**Date:** 2026-02-16
**Script:** `coherence_ops/examples/drift_patch_cycle.py`
**Test:** `tests/test_money_demo.py`

---

## Command

```bash
python -m coherence_ops.examples.drift_patch_cycle
```

## Console Output (Expected)

```
BASELINE  XX.XX (A)
DRIFT     XX.XX (C)   red=1
PATCH     XX.XX (A)   patch=RETCON  drift_resolved=true
Artifacts: examples/demo-stack/drift_patch_cycle_run/
✅ All contract checks passed.
```

Exact scores depend on the sample episode data and the four scoring dimensions (policy_adherence, outcome_health, drift_control, memory_completeness). The contract guarantees:

- DRIFT score is strictly less than BASELINE score (drift_control penalty for 1 red signal)
- PATCH score is strictly greater than DRIFT score (drift signal resolved)
- BASELINE and PATCH scores are equal (both run with zero drift events)

## Artifacts Produced

| # | File | Contents |
|---|------|----------|
| 1 | `report_baseline.json` | CoherenceReport at baseline (no drift) |
| 2 | `report_drift.json` | CoherenceReport after drift injection |
| 3 | `report_after.json` | CoherenceReport after patch resolution |
| 4 | `memory_graph_before.json` | MG snapshot at baseline |
| 5 | `memory_graph_drift.json` | MG snapshot with drift node |
| 6 | `memory_graph_after.json` | MG snapshot with drift + patch nodes |
| 7 | `memory_graph_diff.json` | Diff between baseline and after-patch MG |
| 8 | `loop.mmd` | Mermaid flowchart of the loop |

All artifacts are written to: `examples/demo-stack/drift_patch_cycle_run/`

## Memory Graph Diff Evidence

The `memory_graph_diff.json` file contains:

```json
{
  "added_nodes": ["drift-cycle-001", "patch-cycle-001"],
  "removed_nodes": [],
  "added_edges": [
    ["drift-cycle-001", "resolved_by", "patch-cycle-001"],
    ["<episode-id>", "triggered", "drift-cycle-001"]
  ],
  "removed_edges": [],
  "notes": {
    "baseline_score": "<XX.XX>",
    "drift_score": "<XX.XX>",
    "after_score": "<XX.XX>"
  }
}
```

Key evidence:

- **Patch node added:** `patch-cycle-001` (NodeKind.PATCH)
- **Drift node added:** `drift-cycle-001` (NodeKind.DRIFT)
- **resolved_by edge:** `[drift-cycle-001, "resolved_by", patch-cycle-001]` (EdgeKind.RESOLVED_BY)
- **triggered edge:** `[<episode-id>, "triggered", drift-cycle-001]` (EdgeKind.TRIGGERED)

## Contract Checks

The script runs three internal assertions before printing the final status:

1. **Artifacts present** — all 8 files exist and are non-empty
2. **Score monotonicity** — drift_score < baseline_score AND after_score > drift_score
3. **Diff integrity** — patch node ID in added_nodes, resolved_by edge in added_edges

If any check fails, the script exits with code 1 and prints a diagnostic.

## Smoke Test

```bash
pytest tests/test_money_demo.py -v
```

The smoke test (`tests/test_money_demo.py`) runs the demo end-to-end and verifies:

- All 8 artifacts exist and are non-empty (parametrized)
- Score monotonicity from the diff notes
- Patch node and drift node in added_nodes
- `resolved_by` edge in added_edges
- Mermaid file contains flowchart directive and IDs

## CI Gate

The Money Demo contract test runs in CI on every push to main and every pull request. See `.github/workflows/ci.yml`, step "Run Money Demo contract test".

---

**Σ OVERWATCH** — *Every decision auditable. Every drift detected. Every correction sealed.*
