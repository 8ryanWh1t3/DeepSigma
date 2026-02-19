---
title: "Game Studio Lattice — Runbook"
version: 1.0.0
status: Example
last_updated: 2026-02-19
---

# Game Studio Lattice Runbook

Operational procedures for running the game studio lattice example. Covers scoring,
drift detection, scenario replay, and IRIS queries.

---

## Prerequisites

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt
```

---

## 1. Score the Lattice

Score coherence on the game studio episodes:

```bash
# Score all episodes
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ --json

# Score a specific episode
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ep-gs-001.json --json

# Get letter grade
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ 
# Expected: ~83 → B (baseline) or lower if drift episodes loaded
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

## 2. Run Drift Detection

```bash
# Detect drift across all episodes
python -m coherence_ops.examples.drift_patch_cycle

# Expected output progression:
# BASELINE 83.00 (B) → DRIFT 64.00 (D) → PATCH 76.00 (C)
```

---

## 3. IRIS Queries

### Why was the RONIN DLC rating invalidated?

```bash
python -m coherence_ops iris query --type WHY --target ep-gs-001
```

Expected: Returns the DLR showing Tokyo creative approval → Bucharest QA flag → 
three-domain contradiction across CRE-001, REG-001, PLT-001.

### What drifted in the monetization domain?

```bash
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```

Expected: Returns DS-GS-002 (Founder's Cache contradiction) with the three-way
cascade loop across MON-001, REG-002, CRE-002.

### What assumptions decayed?

```bash
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```

Expected: Shows the `shared-infrastructure` correlation group as the highest-decay
assumption — Source-S003 and S023 proved less independent than assumed.

---

## 4. Scenario Replay

To walk through the four scenarios sequentially:

```bash
# Scenario 1: Rating break
python -m coherence_ops score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-001.json --json

# Scenario 2: Monetization contradiction  
python -m coherence_ops score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-002.json --json

# Scenario 3: Infrastructure cascade
python -m coherence_ops score \
  ./examples/04-game-studio-lattice/episodes/ep-gs-003.json --json

# Scenario 4: Timezone regression
python -m coherence_ops score \
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

## 6. Verification Checklist

After running the example, verify:

| Check | Expected |
|---|---|
| All 4 episodes parse without error | ✅ |
| Baseline score ~83 (B) | ✅ |
| Drift detection identifies all 4 scenarios | ✅ |
| IRIS WHY query returns cross-domain reasoning | ✅ |
| IRIS WHAT_DRIFTED surfaces infrastructure correlation | ✅ |
| Decision episodes are sealed with valid hashes | ✅ |
| Memory Graph shows 4 new governance edges after Scenario 2 | ✅ |

---

## 7. Key Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Lattice structure, node inventory, credibility walkthrough |
| [SCENARIO_PLAN.md](SCENARIO_PLAN.md) | Four drift scenarios with detection, response, seal |
| [SCHEMAS.md](SCHEMAS.md) | JSON schemas with game-studio extensions |
| `episodes/ep-gs-001.json` | Rating break episode |
| `episodes/ep-gs-002.json` | Monetization contradiction episode |
| `episodes/ep-gs-003.json` | Infrastructure cascade episode |
| `episodes/ep-gs-004.json` | Timezone regression episode |
| `drift_signals/` | Drift signal JSON files for each scenario |
