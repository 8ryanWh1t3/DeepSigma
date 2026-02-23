# Issue Closeout: Demo Loop (v0.3 Money Demo)

**Issue:** End-to-end Drift → Patch loop with observable coherence score changes
**Status:** Closed
**Closed by:** v0.3 Money Demo implementation

---

## What Was Implemented

A one-command demo script that runs the complete Drift → Patch cycle:

1. **BASELINE** — Score the system with no drift events
2. **DRIFT** — Inject a red-severity bypass drift signal; score drops
3. **PATCH** — Resolve the drift via RETCON patch; score recovers

The script produces 8 deterministic artifacts including three coherence reports, three memory graph snapshots, a memory graph diff, and a Mermaid diagram.

## How to Run

```bash
python -m coherence_ops.examples.drift_patch_cycle
```

Smoke test:

```bash
pytest tests/test_money_demo.py -v
```

## Files Delivered

| File | Purpose |
|------|---------|
| `coherence_ops/examples/drift_patch_cycle.py` | Main demo script (hardened, with contract checks) |
| `tests/test_money_demo.py` | Smoke test verifying artifacts, scores, diff |
| `examples/demo-stack/drift_patch_cycle_run/.gitkeep` | Output directory placeholder |
| `examples/demo-stack/MONEY_DEMO_EVIDENCE.md` | Evidence file with expected output + diff snippet |
| `.github/workflows/ci.yml` | CI gate running the Money Demo test |
| `metrics/coherence_slos.md` | SLOs aligned to demo outputs |
| `HERO_DEMO.md` | Updated with "Run the Money Demo" section |

## Evidence

Full evidence including console output, artifact list, and memory graph diff snippet:
[examples/demo-stack/MONEY_DEMO_EVIDENCE.md](../../examples/demo-stack/MONEY_DEMO_EVIDENCE.md)

## Acceptance Criteria

- ✅ One command runs end-to-end with no manual JSON edits
- ✅ Produces all 8 artifacts (7 JSON + 1 Mermaid)
- ✅ Shows score drop on DRIFT and improvement on PATCH
- ✅ memory_graph_diff.json includes patch node + resolved_by edge
- ✅ Re-run produces deterministic output (overwrite to fixed directory)
- ✅ Internal contract assertions with clear error messages
- ✅ Smoke test validates all contracts via pytest
- ✅ CI gate fails if Money Demo contract fails
- ✅ SLOs defined and measurable from demo output

---

**Σ OVERWATCH** — *Every decision auditable. Every drift detected. Every correction sealed.*
