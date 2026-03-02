# KPI Contract: Data Integration

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-006 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Measures breadth of connector and schema integration surface. Supports interoperability and ecosystem expansion decisions.

## Formula

```
points = 0
for dir in [connectors, scripts/connectors, docs/docs/connectors,
            docs/docs/integrations, src/deepsigma/connectors,
            src/services, src/demos, docs/examples]:
    if dir exists: points += 1
if schemas/ exists:                     points += 1
if src/ exists and schemas/ exists:     points = max(points, 2)
score = clamp(points * 2, 0, 10)
```

Plain-English: One point per integration directory, doubled, capped at 10.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Connector dirs | `connectors/`, `scripts/connectors/`, etc. | telemetry (directory existence) |
| Schema dir | `schemas/` | telemetry (existence) |
| Source dir | `src/` | telemetry (existence) |

## Cadence

Every release.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 6.0 | No action |
| Yellow | 6.0 > score >= 3.0 | Review integration gaps |
| Red | score < 3.0 | Release blocked |

**Floor:** 3.0
**Max drop:** 1.0

## Failure Modes / Gaming Risks

- **False-high:** Empty connector directories with no actual integration code.
- **False-low:** Connectors organized under non-standard paths not checked.
- **Gaming:** Creating stub directories. Mitigated by connector smoke tests in CI.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | N/A |
| ISO/IEC 25010 | Compatibility (Interoperability), Portability (Adaptability) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
