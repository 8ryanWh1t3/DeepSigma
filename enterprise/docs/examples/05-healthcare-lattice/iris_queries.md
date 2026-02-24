# IRIS Query Pack — Healthcare Lattice

Deterministic query recipes for the Healthcare Lattice example. Each query
demonstrates a different IRIS resolution type against the healthcare episodes
and drift signals.

---

## WHY — Episode 1 (Formulary conflict)

```bash
python -m core iris query --type WHY --target ep-hc-001
```

**Expected (summary):**

- Meridian General updated cardiac formulary without synchronized push to Community
- Patient transfer triggered dispensing conflict (bridge medication not on Community formulary)
- Contradiction across CLN-001, CLN-002, REG-001 (3 Tier 0 claims)
- Credibility Index dropped 87 -> 68 (Elevated risk)
- Recommended patch options A/B/C with CMO + CPO authority
- Selected: Option C — manual bridge protocol + emergency formulary sync

---

## WHY — Episode 2 (Staffing cascade)

```bash
python -m core iris query --type WHY --target ep-hc-002
```

**Expected:**

- Behavioral Health census spike exceeded staffing model capacity
- Float pool depleted; cross-facility staffing ratios degraded
- General and Community nursing ratios dropped below compliance thresholds
- Credibility Index dropped 78 -> 55 (Structural degradation)
- Correlation group: `staffing-model` spans all 3 facilities

---

## WHY — Episode 3 (Billing drift)

```bash
python -m core iris query --type WHY --target ep-hc-003
```

**Expected:**

- Observation-to-inpatient coding template 3 weeks stale vs CMS update
- Revenue anomaly: 34% above expected pattern; potential upcoding exposure
- Estimated exposure $2.1M; affects FIN-002, REG-003, CLN-004
- Credibility Index dropped 70 -> 48 (Compromised)
- Correlation group: `revenue-cycle`

---

## WHY — Episode 4 (Equipment gap)

```bash
python -m core iris query --type WHY --target ep-hc-004
```

**Expected:**

- Night-shift handoff missed final calibration step for 3 cardiac monitors
- False alarm suppression enabled on uncalibrated equipment
- Delayed recognition: 40 minutes before telemetry discrepancy identified
- Credibility Index dropped 62 -> 56 (Structural degradation)
- Correlation group: `biomed-maintenance`

---

## WHAT_DRIFTED — Full inventory

```bash
python -m core iris query --type WHAT_DRIFTED --json
```

**Expected:**

- DS-HC-001 (formulary-mismatch) — RED, CLN/REG/FIN
- DS-HC-002 (staffing-cascade) — RED, OPS/CLN/REG
- DS-HC-003 (billing-drift) — RED, FIN/REG/CLN
- DS-HC-004 (equipment-gap) — YELLOW, OPS/CLN
- `cross-facility-formulary` correlation group elevated as concentration risk
- `revenue-cycle` correlation group flagged for compliance exposure

---

## SHOW — Blast radius (staffing correlation)

```bash
python -m core iris query --type SHOW --target staffing-correlation
```

**Expected:**

- S-HR-001 dependency map across all 3 facilities
- "Float pool depletion cascades across facilities" callout
- Domains impacted: OPS, CLN, REG (3 of 4)
- See: `diagrams/staffing-correlation.mmd`

---

## STATUS — Current lattice health

```bash
python -m core iris query --type STATUS
```

**Expected:**

- Baseline: ~87 / B+ (Minor drift)
- Active drift: 4 signals (3 red, 1 yellow)
- Dominant risk: cross-facility formulary synchronization
- Thin-margin claims: CLN-001 (medication safety), FIN-002 (billing accuracy)
