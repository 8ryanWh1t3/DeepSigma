# KPI Contract: Enterprise Readiness

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-004 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Confirms operational documentation and governance guardrails are in place. Supports enterprise deployment and compliance decisions.

## Formula

```
points = 0
if BRANCH_PROTECTION.md exists:       points += 1
if PILOT_CONTRACT_ONEPAGER.md exists:  points += 1
if .github/workflows/kpi.yml exists:   points += 1
if .github/workflows/kpi_gate.yml:     points += 1
if Makefile exists:                    points += 1
score = clamp(points * 2, 0, 10)
```

Plain-English: One point per governance artifact, doubled, capped at 10.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Branch protection docs | `BRANCH_PROTECTION.md` | telemetry (existence) |
| Pilot contract | `PILOT_CONTRACT_ONEPAGER.md` | telemetry (existence) |
| KPI workflow | `.github/workflows/kpi.yml` | telemetry (existence) |
| KPI gate workflow | `.github/workflows/kpi_gate.yml` | telemetry (existence) |
| Build system | `Makefile` | telemetry (existence) |

## Cadence

Every release.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 6.0 | No action |
| Yellow | 6.0 > score >= 3.0 | Document gaps |
| Red | score < 3.0 | Release blocked |

**Floor:** 3.0
**Max drop:** 1.0

## Failure Modes / Gaming Risks

- **False-high:** Placeholder documents that satisfy existence checks without real content.
- **False-low:** Governance docs stored in non-standard locations.
- **Gaming:** Creating stub files. Mitigated by content review in PR process.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | N/A |
| ISO/IEC 25010 | Compatibility (Co-existence), Usability (Operability) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
