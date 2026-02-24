# Healthcare Lattice — Multi-Facility Health System

**~300 nodes. Three hospitals. Four drift events in 48 hours.**

A fictional multi-hospital health system (Meridian Health Partners) demonstrating how
clinical, regulatory, operational, and financial decisions create cross-domain
contradictions that compound across shift boundaries.

## Guardrails

Fictional health system, fictional facilities, fictional data. **No real hospital,
patient, clinician, payer, or regulatory body is represented.** No clinical advice is
given or implied. All patient identifiers are synthetic. Demonstrates institutional
credibility architecture applied to healthcare operations governance.

---

## 60-Second Quickstart

```bash
# 1. Validate all example JSON
python examples/04-game-studio-lattice/tools/validate_example_json.py \
  --episodes examples/05-healthcare-lattice/episodes \
  --drift    examples/05-healthcare-lattice/drift_signals \
  --patches  examples/05-healthcare-lattice/patches

# 2. View baseline credibility score
cat examples/05-healthcare-lattice/expected_outputs/score-baseline.json | python -m json.tool

# 3. View post-drift score (formulary conflict)
cat examples/05-healthcare-lattice/expected_outputs/score-ep-hc-001.json | python -m json.tool

# 4. Run drift-patch cycle with healthcare context
python -m core.examples.drift_patch_cycle --example healthcare

# 5. Render a Mermaid diagram
cat examples/05-healthcare-lattice/diagrams/formulary-cascade.mmd
```

---

## Lattice Topology

| Domain | Code | Claims | Key Sources |
|--------|------|--------|-------------|
| Clinical Governance | CLN | ~12 | EHR audit, pharmacy, clinical decision support |
| Regulatory Compliance | REG | ~10 | Survey readiness, incident reporting, compliance dashboards |
| Operational Continuity | OPS | ~14 | HR/scheduling, inventory, biomed tracking |
| Financial Integrity | FIN | ~10 | Revenue cycle, claims adjudication, cost accounting |

### Facilities

| Facility | Beds | Specialties |
|----------|------|------------|
| Meridian General | 450 | Trauma Level II, cardiac, oncology |
| Meridian Community | 180 | General surgery, maternity, pediatrics |
| Meridian Behavioral | 60 | Inpatient behavioral health, crisis stabilization |

---

## Scenarios

| # | Episode | Severity | Domains | CI Impact |
|---|---------|----------|---------|-----------|
| 1 | [Formulary Conflict](episodes/ep-hc-001.json) | Red | CLN, REG, FIN | 87 → 68 |
| 2 | [Staffing Cascade](episodes/ep-hc-002.json) | Red | OPS, REG, CLN, FIN | 79 → 55 |
| 3 | [Billing Code Drift](episodes/ep-hc-003.json) | Red | FIN, REG, CLN | 70 → 48 |
| 4 | [Equipment Gap](episodes/ep-hc-004.json) | Yellow | OPS, CLN | 62 → 56 |

## Diagrams

| Diagram | File | Description |
|---------|------|-------------|
| Formulary Cascade | [formulary-cascade.mmd](diagrams/formulary-cascade.mmd) | P&T approval → sync lag → transfer conflict |
| Staffing Correlation | [staffing-correlation.mmd](diagrams/staffing-correlation.mmd) | Census surge → shared pool depletion → 4-domain cascade |
| Drift to Patch | [drift-to-patch.mmd](diagrams/drift-to-patch.mmd) | Generic evidence → claim → drift → patch → seal sequence |

## Key Files

| Path | Description |
|------|-------------|
| [SCENARIO_PLAN.md](SCENARIO_PLAN.md) | Full narrative for all 4 scenarios |
| [episodes/](episodes/) | 4 DecisionEpisodes (ep-hc-001..004) |
| [drift_signals/](drift_signals/) | 4 DriftSignals (ds-hc-001..004) |
| [patches/](patches/) | 2 Patch artifacts (patch-hc-001..002) |
| [diagrams/](diagrams/) | 3 Mermaid diagrams |
| [expected_outputs/](expected_outputs/) | Baseline + post-drift score snapshots |

---

## What This Example Teaches

- **Formulary changes have cross-facility blast radius** — a P&T Committee decision
  creates patient safety risk when interface synchronization lags across facilities
- **Shared resource pools create hidden dependencies** — workforce allocation across
  facilities is a correlation group
- **Financial drift has regulatory gravity** — billing template changes accumulate
  material false claims exposure silently
- **Shift boundaries amplify operational drift** — the healthcare equivalent of
  timezone drift in the game studio lattice
