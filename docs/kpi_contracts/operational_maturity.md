# KPI Contract: Operational Maturity

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-008 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Confirms presence of pilot tooling, reporting infrastructure, and operational runbooks. Supports operational readiness and deployment confidence decisions.

## Formula

```
points = 0
if pilot_in_a_box.py exists:       points += 2
if why_60s_challenge.py exists:     points += 1
if pilot/reports/ exists:           points += 2
if coherence_ci.yml exists:         points += 2
if ci_report.json parseable:        points += 1
score = clamp(points * 1.25, 0, 10)
```

Plain-English: Weighted check for pilot tools, reports directory, CI workflow, and report parsability, scaled by 1.25×, capped at 10.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Pilot script | `enterprise/scripts/pilot_in_a_box.py` | telemetry (existence) |
| 60s challenge | `enterprise/scripts/why_60s_challenge.py` | telemetry (existence) |
| Pilot reports | `pilot/reports/` | telemetry (directory existence) |
| Coherence CI | `.github/workflows/coherence_ci.yml` | telemetry (existence) |
| CI report | `pilot/reports/ci_report.json` | telemetry (parse check) |

## Cadence

Every release.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 7.0 | No action |
| Yellow | 7.0 > score >= 4.0 | Review operational gaps |
| Red | score < 4.0 | Release blocked |

**Floor:** 4.0
**Max drop:** 1.0

## Failure Modes / Gaming Risks

- **False-high:** Scripts exist but are non-functional. Mitigated by CI execution tests.
- **False-low:** Reports generated but stored in non-standard locations.
- **Gaming:** Creating stub scripts. Mitigated by smoke test requirements.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | Change Failure Rate (partial — maturity tooling reduces failure rate); MTTR (partial — pilot tooling accelerates recovery) |
| ISO/IEC 25010 | Reliability (Maturity, Availability, Recoverability) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
