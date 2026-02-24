---
title: "Healthcare Lattice — Scenario Plan"
version: 1.0.0
status: Example
last_updated: 2026-02-19
---

# Healthcare Lattice Scenario Plan

**~300 nodes. Three hospitals. Four drift events in 48 hours.**

This scenario plan walks through four drift events characteristic of multi-facility
healthcare system governance. Each event demonstrates how clinical, regulatory, operational,
and financial decisions create cross-domain contradictions that compound across shift
boundaries.

---

## Guardrails

Fictional health system (Meridian Health Partners), fictional facilities, fictional data.
Demonstrates institutional credibility architecture applied to healthcare operations
governance. **No real hospital, patient, clinician, payer, or regulatory body is
represented.** No clinical advice is given or implied. All patient identifiers are synthetic.

---

## Lattice Topology

| Domain | Code | Description | Claims | Evidence Sources |
|--------|------|-------------|--------|-----------------|
| Clinical Governance | CLN | Protocol adherence, formulary compliance, care pathway integrity | ~12 | EHR audit, pharmacy systems, clinical decision support |
| Regulatory Compliance | REG | CMS conditions of participation, state licensure, accreditation standards | ~10 | Survey readiness tools, incident reporting, compliance dashboards |
| Operational Continuity | OPS | Staffing ratios, bed capacity, supply chain, equipment maintenance | ~14 | HR/scheduling systems, inventory management, biomed tracking |
| Financial Integrity | FIN | Billing accuracy, payer contract compliance, cost allocation | ~10 | Revenue cycle systems, claims adjudication, cost accounting |

### Facilities

| Facility | Location | Beds | Specialties |
|----------|----------|------|------------|
| Meridian General | Metro campus | 450 | Trauma Level II, cardiac, oncology |
| Meridian Community | Suburban campus | 180 | General surgery, maternity, pediatrics |
| Meridian Behavioral | Satellite facility | 60 | Inpatient behavioral health, crisis stabilization |

### Key Sources

| Source ID | Name | Facility | Domains |
|-----------|------|----------|---------|
| S-EHR-001 | Epic EHR Audit Feed | All | CLN, REG |
| S-RX-001 | Pharmacy Dispensing System | All | CLN, FIN |
| S-HR-001 | Workforce Management | All | OPS |
| S-REV-001 | Revenue Cycle Platform | All | FIN, REG |
| S-BIO-001 | Biomedical Equipment Tracking | General, Community | OPS, CLN |
| S-INC-001 | Incident Reporting System | All | REG, CLN, OPS |
| S-SUP-001 | Supply Chain Management | All | OPS, FIN |

---

## Baseline State

| Metric | Value |
|--------|-------|
| Credibility Index | 87 (Minor drift) |
| Active drift signals | 1 (yellow — pending formulary update at Community) |
| Open patches | 0 |
| Domains at risk | CLN (formulary lag) |

The health system is in routine operating state. One minor drift signal tracks a
formulary synchronization delay between General and Community. All three facilities
are within staffing ratios. Meridian General's Joint Commission survey is 90 days out.

---

## Scenario 1: Formulary Conflict Creates Medication Safety Risk (T₀ + 0h)

### Trigger

Meridian General's Pharmacy & Therapeutics Committee approves adding a new anticoagulant
(fictional: Coagulase-X) to the system formulary, replacing the existing agent for
post-surgical prophylaxis. The approval is logged in S-RX-001 at 10:00 ET.

Meridian Community's pharmacy system (same S-RX-001 source, different facility instance)
does not receive the formulary update due to an interface lag. At 14:00 ET, Community's
surgeon prescribes the *old* anticoagulant per standing protocol. The patient is
transferred to General at 18:00 ET for monitoring. General's clinical decision support
flags a drug interaction between the old anticoagulant and the new formulary's default
bridge protocol.

### Detection

| Signal | Value | Category |
|--------|-------|----------|
| Formulary mismatch | Community prescribing non-formulary agent post-update | Cross-facility contradiction |
| Severity | **Red** | |
| Domains affected | CLN, REG, FIN | |
| Affected claims | CLN-001 (formulary compliance), CLN-002 (medication safety), REG-001 (CMS medication management) |
| Cross-facility | Yes — General formulary vs Community dispensing |
| Time-to-detection | **8 hours** (approval → transfer flag) |

### Response

| Action | Detail |
|--------|--------|
| DS artifact | Formulary mismatch, red, CLN+REG+FIN, cross-facility, 3 Tier 0 claims |
| Root cause | EHR interface lag between General and Community pharmacy instances; no real-time formulary sync |
| Patch option A | Emergency formulary push to Community (4-hour implementation) |
| Patch option B | Revert General to old formulary until sync verified (disrupts new protocol) |
| Patch option C | Manual bridge protocol for transfer patients until sync completes |
| Selected | C (immediate safety), then A (systemic fix) |
| MG update | Formulary change → mandatory cross-facility sync verification gate added |
| Seal | DecisionEpisode `ep-hc-001` sealed |

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 87 | Minor drift |
| During drift | **68** | Elevated risk |
| After patch | 79 | Elevated risk |

---

## Scenario 2: Staffing Ratio Breach Triggers Regulatory Cascade (T₀ + 12h)

### Trigger

A seasonal respiratory illness surge increases Meridian General's census by 22% over
48 hours. The nursing staffing ratio for medical-surgical units drops below the
state-mandated minimum (1:5) to effective 1:7 on night shift. S-HR-001 flags the
breach at 02:00 ET.

Simultaneously, the surge diverts travel nurse contracts from Community to General,
dropping Community's labor & delivery staffing below its own minimum threshold.

### Detection

| Signal | Value | Category |
|--------|-------|----------|
| Staffing ratio breach | General med-surg 1:7 (mandate: 1:5) | Regulatory — operational failure |
| Cascade | Community L&D staffing below threshold due to diversion | Cross-facility resource competition |
| Severity | **Red** | |
| Domains affected | OPS, REG, CLN, FIN | |
| Affected claims | OPS-001 (staffing compliance), REG-002 (state licensure), CLN-003 (care quality), FIN-001 (overtime cost) |
| Correlation group | `workforce-shared-pool` | |

### Response

| Action | Detail |
|--------|--------|
| DS artifact | Staffing cascade, red, 4 domains, correlation group `workforce-shared-pool` |
| Root cause | Shared travel nurse pool with no cross-facility allocation governance |
| Immediate | Activate agency staffing for General night shift; restore Community L&D contracts |
| Patch 1 (OPS) | Cross-facility staffing allocation model with minimum reserve per facility |
| Patch 2 (REG) | State notification of corrective action plan within 24 hours |
| MG update | Staffing reallocation now requires system-level approval when any facility is within 10% of minimum |
| Seal | DecisionEpisode `ep-hc-002` sealed |

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 79 | Elevated risk |
| During drift | **55** | Structural degradation |
| After patch | 70 | Elevated risk |

---

## Scenario 3: Billing Code Drift Creates False Claims Risk (T₀ + 24h)

### Trigger

Meridian General's revenue cycle team discovers that a coding template update pushed
3 weeks ago has been silently upcoding observation stays as inpatient admissions for
patients with specific cardiac diagnoses. S-REV-001 audit detects a 34% increase in
cardiac inpatient revenue that does not correlate with census changes.

The template was approved by General's coding manager but was not reviewed against
CMS billing rules updated 6 weeks ago. The new CMS rules tightened the criteria for
inpatient-vs-observation classification for the affected diagnosis codes.

### Detection

| Signal | Value | Category |
|--------|-------|----------|
| Billing classification drift | Observation → Inpatient upcoding, 34% revenue anomaly | Financial — compliance breach |
| Severity | **Red** | |
| Domains affected | FIN, REG, CLN | |
| Affected claims | FIN-002 (billing accuracy), REG-003 (CMS billing compliance), CLN-004 (clinical documentation integrity) |
| Estimated exposure | ~$2.1M in potentially improper claims over 3 weeks |
| Cross-domain | Yes — financial template change affects regulatory compliance and clinical documentation |

### Response

| Action | Detail |
|--------|--------|
| DS artifact | Billing classification drift, red, FIN+REG+CLN, 3 Tier 0 claims, $2.1M exposure |
| Root cause | Coding template update not validated against current CMS rules; no automated rule-check gate |
| Immediate | Suspend affected template; manual review queue for flagged claims |
| Patch 1 (FIN) | Correct template; re-adjudicate affected claims |
| Patch 2 (REG) | Self-disclosure to CMS/OIG with corrective action plan |
| MG update | Coding template changes now require automated CMS rule validation + compliance sign-off |
| Seal | DecisionEpisode `ep-hc-003` sealed |

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 70 | Elevated risk |
| During drift | **48** | Compromised |
| After patch | 62 | Structural degradation |

---

## Scenario 4: Equipment Maintenance Lapse — Shift Handoff Gap (T₀ + 36h)

### Trigger

Meridian General's biomedical engineering team completes preventive maintenance on
12 cardiac monitors in the CICU. The maintenance completion is logged in S-BIO-001
at 16:00 ET by the day shift biomed tech. However, the tech marks 3 monitors as
"returned to service" when they are still awaiting final calibration verification —
a step that requires a second technician who has already left for the day.

Night shift nursing pulls the 3 unverified monitors into service at 20:00 ET during
the census surge from Scenario 2. At 03:00 ET, one monitor produces a false-negative
alarm suppression, delaying recognition of a patient's rhythm change by 40 minutes.

### Detection

| Signal | Value | Category |
|--------|-------|----------|
| Equipment verification gap | 3 monitors returned to service without calibration check | Operational — shift handoff failure |
| Severity | **Yellow** | |
| Domains affected | OPS, CLN | |
| Affected claims | OPS-003 (equipment readiness), CLN-005 (monitoring integrity) |
| Cross-domain | Yes — operational handoff gap creates clinical risk |

### Response

| Action | Detail |
|--------|--------|
| DS artifact | Equipment verification gap, yellow, OPS+CLN, shift handoff failure |
| Root cause | S-BIO-001 allows single-tech sign-off on multi-step maintenance; no calibration gate |
| Immediate | Pull 3 monitors from service; emergency calibration by on-call biomed |
| Patch | Add two-step verification in S-BIO-001: maintenance complete ≠ returned to service |
| MG update | Equipment maintenance now requires independent verification before return-to-service |
| Seal | DecisionEpisode `ep-hc-004` sealed |

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 62 | Structural degradation |
| During drift | 56 | Structural degradation |
| After patch | 65 | Structural degradation |

---

## Cumulative Timeline

```
T₀+0h       T₀+12h      T₀+24h       T₀+36h      T₀+48h
│            │            │             │            │
Formulary    Staffing     Billing       Equipment    Stabilized
conflict     cascade      drift         gap
CI: 87→68    CI: 79→55    CI: 70→48     CI: 62→56    CI: ~65
Red          Red          Red           Yellow       Recovery
```

### Final State (T₀ + 48h)

| Metric | Before | After |
|--------|--------|-------|
| Credibility Index | 87 | 65 |
| Band | Minor drift | Structural degradation |
| Sealed episodes | 0 | 4 |
| Open patches | 0 | 3 |
| Governance changes | 0 | 5 new edges in Memory Graph |
| Joint Commission readiness | On track | At risk — corrective actions required |

---

## What This Scenario Plan Teaches

**Formulary changes have cross-facility blast radius.** Scenario 1 shows that a
P&T Committee decision — made within proper clinical governance — creates patient safety
risk when interface synchronization lags across facilities.

**Shared resource pools create hidden dependencies.** Scenario 2 demonstrates that
workforce allocation across facilities is a correlation group. Solving one facility's
staffing crisis by drawing from another creates a cascade.

**Financial drift has regulatory gravity.** Scenario 3 proves that billing template
changes, if not validated against current rules, can accumulate material false claims
exposure silently over weeks.

**Shift boundaries amplify operational drift.** Scenario 4 shows that equipment
maintenance workflows with single-person sign-off create verification gaps at shift
handoffs — the same timezone-equivalent problem as the game studio lattice.

**Healthcare drift compounds faster than other verticals.** Patient safety claims
(Tier 0) combined with regulatory obligations mean the institution cannot tolerate
sustained elevated risk without external reporting obligations triggering.
