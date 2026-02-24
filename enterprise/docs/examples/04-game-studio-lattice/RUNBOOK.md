---
title: "Game Studio Lattice — Runbook"
version: 1.1.0
status: Example
last_updated: 2026-02-19
---

# Game Studio Lattice Runbook

Operational procedures for running the game studio lattice example. Covers scoring,
drift detection, scenario replay, IRIS queries, validation, and workbook generation.

---

## Prerequisites

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -e .
pip install openpyxl   # for workbook generation
```

---

## 1. Score the Lattice

Score coherence on the game studio episodes:

```bash
# Score all episodes
python -m core score ./examples/04-game-studio-lattice/episodes/ --json

# Score a specific episode
python -m core score ./examples/04-game-studio-lattice/episodes/ep-gs-001.json --json

# Get letter grade
python -m core score ./examples/04-game-studio-lattice/episodes/
# Expected: ~83 -> B (baseline) or lower if drift episodes loaded
```

### Expected Baseline Output

```
Coherence Score: 83.00 (B)
Grade: B
Drift Signals: 2 (yellow)
Domains: 6
Claims: 28 (12 Tier 0)
Evidence: 282
```

---

## 2. Run Drift -> Patch Cycle

```bash
# Full game-studio example (loads episodes, drift signals, patches)
python -m core.examples.drift_patch_cycle --example game-studio

# Default money demo (for comparison)
python -m core.examples.drift_patch_cycle
```

Expected output for game-studio:
- 4 episodes loaded
- 4 drift signals detected (3 RED, 1 YELLOW)
- 4 patch plans with closure conditions
- Score progression: 83 -> 41 (worst) -> recovery

---

## 3. IRIS Queries

### Why was the RONIN DLC rating invalidated?

```bash
python -m core iris query --type WHY --target ep-gs-001
```

Expected: Returns the DLR showing Tokyo creative approval -> Bucharest QA flag ->
three-domain contradiction across CRE-001, REG-001, PLT-001.

### What drifted in the monetization domain?

```bash
python -m core iris query --type WHAT_DRIFTED --json
```

Expected: Returns DS-GS-001..004 with the four scenario drift signals, plus
`shared-infrastructure` correlation group flagged as concentration risk.

### Full IRIS query pack

See [iris_queries.md](iris_queries.md) for the complete set of queries with expected outputs.
Expected output stubs are in `expected_outputs/`.

---

## 4. Scenario Replay

To walk through the four scenarios sequentially:

```bash
# Scenario 1: Rating break
python -m core score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-001.json --json

# Scenario 2: Monetization contradiction
python -m core score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-002.json --json

# Scenario 3: Infrastructure cascade
python -m core score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-003.json --json

# Scenario 4: Timezone regression
python -m core score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-004.json --json
```

### Cumulative Score Progression

| Episode | Event | Score Before | Score After | Band |
|---|---|---|---|---|
| ep-gs-001 | Rating break | 83 | 64 | Structural degradation |
| ep-gs-002 | Monetization contradiction | 76 | 52 | Structural degradation |
| ep-gs-003 | Infrastructure cascade | 71 | 41 | Compromised |
| ep-gs-004 | Timezone regression | 69 | 63 | Structural degradation |

---

## 5. Drift Signals

View the drift signal files:

```bash
ls ./examples/04-game-studio-lattice/drift_signals/

# ds-gs-001-rating-mismatch.json
# ds-gs-002-monetization-contradiction.json
# ds-gs-003-infrastructure-cascade.json
# ds-gs-004-timezone-regression.json
```

Each signal file conforms to the drift signal schema in [SCHEMAS.md](SCHEMAS.md) with
game-studio-specific extensions.

---

## 6. Patch Artifacts

View the patch plans:

```bash
ls ./examples/04-game-studio-lattice/patches/

# patch-gs-001-rating-envelope.json
# patch-gs-002-founders-cache.json
# patch-gs-003-shared-infra.json
# patch-gs-004-timezone-regression.json
```

Each patch includes decision options, selected option, step-by-step sequence with
owners and rollback plans, and closure conditions.

---

## 7. Validate Example JSON

```bash
python ./examples/04-game-studio-lattice/tools/validate_example_json.py
```

Checks all episodes, drift signals, and patches for required keys. Exits non-zero
on failure. Uses only stdlib.

---

## 8. Generate GameOps Workbook

```bash
python ./examples/04-game-studio-lattice/tools/generate_gamestudio_workbook.py \
  --out ./examples/04-game-studio-lattice/GameOps_Workbook.xlsx
```

Generates an Excel workbook with 8 tabs:
- BalanceChanges, EconomyTuning, FeatureCuts, Assumptions
- DriftSignals, PatchPlans, CanonRules
- PROMPTS (LLM interaction surface with system prompt)

Each tab has 25 synthetic rows cross-referenced to ep-gs-XXX, DS-GS-XXX, Patch-GS-XXX.
Requires `openpyxl`.

---

## 9. Verification Checklist

After running the example, verify:

| Check | Expected |
|---|---|
| All 4 episodes parse without error | Valid JSON |
| All 4 drift signals parse without error | Valid JSON |
| All 4 patches parse without error | Valid JSON |
| Baseline score ~83 (B) | ~83 / B |
| Drift detection identifies all 4 scenarios | 4 signals |
| IRIS WHY query returns cross-domain reasoning | Resolved |
| IRIS WHAT_DRIFTED surfaces infrastructure correlation | 4 signals |
| Patch plans have closure conditions | 4 plans |
| Validator returns all-pass | 12 files |
| Workbook generates with 8 tabs | .xlsx created |

---

## 10. Key Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Lattice structure, node inventory, credibility walkthrough |
| [SCENARIO_PLAN.md](SCENARIO_PLAN.md) | Four drift scenarios with detection, response, seal |
| [SCHEMAS.md](SCHEMAS.md) | JSON schemas with game-studio extensions |
| [iris_queries.md](iris_queries.md) | IRIS query pack with expected outputs |
| `episodes/` | 4 decision episode JSON files |
| `drift_signals/` | 4 drift signal JSON files |
| `patches/` | 4 patch plan JSON files |
| `diagrams/` | 3 Mermaid diagrams (contradiction loop, blast radius, drift-to-patch) |
| `expected_outputs/` | Expected output stubs for deterministic demos |
| `tools/validate_example_json.py` | JSON validation harness |
| `tools/generate_gamestudio_workbook.py` | Excel workbook generator |
