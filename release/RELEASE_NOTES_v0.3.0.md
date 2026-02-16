---
title: "Release Notes — v0.3.0 Living Memory"
version: "0.3.0"
codename: "Living Memory"
date: "2026-02-16"
---

# v0.3.0 — Living Memory

**Release date:** 2026-02-16

> From sealed decisions to self-correcting institutional memory (Drift → Patch in minutes).

## What "Living Memory" Means

Before v0.3, the Coherence Ops pipeline could seal decisions, detect drift, and score coherence — but the full loop (decision → drift → patch → memory update → score improvement) required manual assembly. v0.3.0 closes that loop in a single command. The Memory Graph now records not just what happened, but what broke and how it was fixed. Institutional memory is no longer a snapshot — it is alive, self-correcting, and auditable.

## What's New

- **Money Demo** — One-command Drift → Patch cycle (`python -m coherence_ops.examples.drift_patch_cycle`) producing 8 deterministic artifacts: 3 coherence reports, 3 MG snapshots, a memory graph diff, and a Mermaid diagram
- **Contract Assertions** — Built-in score monotonicity checks (drift < baseline, patch > drift), artifact existence verification, and diff integrity validation
- **CI Gate** — 16-test smoke suite runs on every push to `main` and every PR; CI fails if the Money Demo contract breaks
- **Coherence SLOs** — 8 enforceable Service Level Objectives aligned to Money Demo outputs (`metrics/coherence_slos.md`)
- **Deterministic Scores** — Baseline 90.00 (A), Drift 85.75 (B), After Patch 90.00 (A) — reproducible on every run
- **Evidence Package** — `MONEY_DEMO_EVIDENCE.md` with console output, artifact manifest, diff snippet, and contract checks
- **Issue #8 Closeout** — Full acceptance criteria documented in `docs/issue_closeouts/issue_8_demo_loop.md`

## Run the Money Demo

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -e ".[dev]"
python -m coherence_ops.examples.drift_patch_cycle
```

**Expected output:**

```
BASELINE  90.00 (A)
DRIFT    85.75 (B)   red=1
PATCH    90.00 (A)   patch=RETCON  drift_resolved=true
Artifacts: examples/demo-stack/drift_patch_cycle_run/
✅ All contract checks passed.
```

**Artifacts produced** (in `examples/demo-stack/drift_patch_cycle_run/`):

| File | Contents |
|------|----------|
| `report_baseline.json` | Coherence score at baseline (no drift) |
| `report_drift.json` | Score after 1 red bypass drift |
| `report_after.json` | Score after RETCON patch |
| `memory_graph_before.json` | MG snapshot before drift |
| `memory_graph_drift.json` | MG snapshot with drift node |
| `memory_graph_after.json` | MG snapshot with drift + patch nodes |
| `memory_graph_diff.json` | Diff showing added nodes and resolved_by edge |
| `loop.mmd` | Mermaid flowchart of the Drift → Patch loop |

## Key Links

| Resource | Path |
|----------|------|
| Front door | [START_HERE.md](../START_HERE.md) |
| Hero demo (full walkthrough) | [HERO_DEMO.md](../HERO_DEMO.md) |
| Canonical specs | [/canonical/](../canonical/) |
| Coherence SLOs | [metrics/coherence_slos.md](../metrics/coherence_slos.md) |
| Money Demo evidence | [MONEY_DEMO_EVIDENCE.md](../examples/demo-stack/MONEY_DEMO_EVIDENCE.md) |
| Changelog | [CHANGELOG.md](../CHANGELOG.md) |

## Smoke Test

```bash
pytest tests/test_money_demo.py -v
# Expected: 16 passed
```

---

**Σ OVERWATCH** — *Every decision auditable. Every drift detected. Every correction sealed.*
