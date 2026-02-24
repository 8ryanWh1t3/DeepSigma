---
title: "Healthcare Lattice — Runbook"
version: 1.1.0
status: Example
last_updated: 2026-02-19
---

# Healthcare Lattice Runbook

Operational procedures for running the healthcare lattice example. Covers scoring,
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

Score coherence on the healthcare episodes:

```bash
# Score all episodes
python -m core score ./examples/05-healthcare-lattice/episodes/ --json

# Score a specific episode
python -m core score ./examples/05-healthcare-lattice/episodes/ep-hc-001.json --json

# Get letter grade
python -m core score ./examples/05-healthcare-lattice/episodes/
# Expected: ~87 -> B+ (baseline) or lower if drift episodes loaded
```

### Expected Baseline Output

```
Coherence Score: 87.00 (B+)
Grade: B+
Drift Signals: 0
Domains: 4 (CLN, REG, OPS, FIN)
Claims: ~46
Evidence: ~300 nodes across 3 facilities
```

---

## 2. Run Drift -> Patch Cycle

```bash
# Full healthcare example (loads episodes, drift signals, patches)
python -m core.examples.drift_patch_cycle --example healthcare

# Default money demo (for comparison)
python -m core.examples.drift_patch_cycle
```

Expected output for healthcare:
- 4 episodes loaded
- 4 drift signals detected (3 RED, 1 YELLOW)
- 4 patch plans with closure conditions
- Score progression: 87 -> 48 (worst) -> recovery

---

## 3. IRIS Queries

### Why did the formulary conflict occur?

```bash
python -m core iris query --type WHY --target ep-hc-001
```

Expected: Returns the DLR showing formulary synchronization drift across
Meridian General and Community — clinical safety + compliance + revenue impact.

### What drifted in the healthcare system?

```bash
python -m core iris query --type WHAT_DRIFTED --json
```

Expected: Returns DS-HC-001..004 with the four scenario drift signals, plus
`cross-facility-formulary` and `revenue-cycle` correlation groups flagged.

### Full IRIS query pack

See [iris_queries.md](iris_queries.md) for the complete set of queries with expected outputs.
Expected output stubs are in `expected_outputs/`.

---

## 4. Scenario Replay

To walk through the four scenarios sequentially:

```bash
# Scenario 1: Formulary conflict
python -m core score \
  ./examples/05-healthcare-lattice/episodes/ep-hc-001.json --json

# Scenario 2: Staffing cascade
python -m core score \
  ./examples/05-healthcare-lattice/episodes/ep-hc-002.json --json

# Scenario 3: Billing drift
python -m core score \
  ./examples/05-healthcare-lattice/episodes/ep-hc-003.json --json

# Scenario 4: Equipment gap
python -m core score \
  ./examples/05-healthcare-lattice/episodes/ep-hc-004.json --json
```

### Cumulative Score Progression

| Episode | Event | Score Before | Score After | Band |
|---|---|---|---|---|
| ep-hc-001 | Formulary conflict | 87 | 68 | Elevated risk |
| ep-hc-002 | Staffing cascade | 78 | 55 | Structural degradation |
| ep-hc-003 | Billing drift | 70 | 48 | Compromised |
| ep-hc-004 | Equipment gap | 62 | 56 | Structural degradation |

---

## 5. Drift Signals

View the drift signal files:

```bash
ls ./examples/05-healthcare-lattice/drift_signals/

# ds-hc-001-formulary-mismatch.json
# ds-hc-002-staffing-cascade.json
# ds-hc-003-billing-drift.json
# ds-hc-004-equipment-gap.json
```

Each signal file conforms to the drift signal schema with healthcare-specific
extensions (facilities, correlation groups, clinical/financial impact).

---

## 6. Patch Artifacts

View the patch plans:

```bash
ls ./examples/05-healthcare-lattice/patches/

# patch-hc-001-formulary-sync.json
# patch-hc-002-staffing-model.json
# patch-hc-003-billing-drift.json
# patch-hc-004-equipment-gap.json
```

Each patch includes decision options, selected option, step-by-step sequence with
owners and rollback plans, and closure conditions.

---

## 7. Validate Example JSON

```bash
python ./examples/05-healthcare-lattice/tools/validate_example_json.py
```

Checks all episodes, drift signals, and patches for required keys. Exits non-zero
on failure. Uses only stdlib.

---

## 8. Generate CareOps Workbook

```bash
python ./examples/05-healthcare-lattice/tools/generate_healthcare_workbook.py \
  --out ./examples/05-healthcare-lattice/CareOps_Workbook.xlsx
```

Generates an Excel workbook with 9 tabs:
- ClinicalDecisions, StaffingModels, FormularyChanges, BillingRules, Assumptions
- DriftSignals, PatchPlans, CanonRules
- PROMPTS (LLM interaction surface with system prompt)

Each tab has 25 synthetic rows cross-referenced to ep-hc-XXX, DS-HC-XXX, Patch-HC-XXX.
Requires `openpyxl`.

---

## 9. Roles

| Role | Responsibility |
|---|---|
| Clinical Lead | Protocol adherence, formulary governance, care pathway integrity |
| Compliance/Privacy | CMS conditions of participation, accreditation, HIPAA |
| Revenue Cycle | Billing accuracy, coding compliance, denial management |
| Ops/Staffing | Staffing ratios, bed capacity, supply chain, equipment maintenance |
| Data/Telemetry | EHR integration, claims data, clinical decision support |

---

## 10. Operational Checklist

When a drift signal is detected:

1. **Triage** — Assess severity (RED/YELLOW) and domains affected
2. **Correlation** — Check correlation-group risk (cross-facility? cross-domain?)
3. **Select** — Choose patch option from decision options matrix
4. **Execute** — Follow patch sequence with owner assignments
5. **Verify** — Confirm each step's verification condition
6. **Rollback** — If verification fails, execute rollback plan
7. **Close** — Confirm all closure conditions met

---

## 11. Verification Checklist

After running the example, verify:

| Check | Expected |
|---|---|
| All 4 episodes parse without error | Valid JSON |
| All 4 drift signals parse without error | Valid JSON |
| All 4 patches parse without error | Valid JSON |
| Baseline score ~87 (B+) | ~87 / B+ |
| Drift detection identifies all 4 scenarios | 4 signals |
| IRIS WHY query returns cross-domain reasoning | Resolved |
| IRIS WHAT_DRIFTED surfaces correlation groups | 4 signals |
| Patch plans have closure conditions | 4 plans |
| Validator returns all-pass | 12 files |
| Workbook generates with 9 tabs | .xlsx created |

---

## 12. Key Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Lattice structure, node inventory, credibility walkthrough |
| [SCENARIO_PLAN.md](SCENARIO_PLAN.md) | Four drift scenarios with detection, response, seal |
| [iris_queries.md](iris_queries.md) | IRIS query pack with expected outputs |
| `episodes/` | 4 decision episode JSON files |
| `drift_signals/` | 4 drift signal JSON files |
| `patches/` | 4 patch plan JSON files |
| `diagrams/` | 3 Mermaid diagrams (formulary cascade, staffing correlation, drift-to-patch) |
| `expected_outputs/` | Expected output stubs for deterministic demos |
| `tools/validate_example_json.py` | JSON validation harness |
| `tools/generate_healthcare_workbook.py` | CareOps Excel workbook generator |
