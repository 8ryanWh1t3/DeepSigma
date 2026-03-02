# KPI Contract: Automation Depth

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-002 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Measures breadth and density of CI/CD automation. Supports decisions about pipeline maturity and deployment confidence.

## Formula

```
score = min(
    (workflow_count * 1.2) +
    (scripts_count / 30 * 4) +
    (2.0 if Makefile exists else 0),
    10.0
)
```

Plain-English: Weighted count of workflows, automation scripts, and build tooling presence, capped at 10.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| CI workflows | `.github/workflows/*.{yml,yaml}` | telemetry (file count) |
| Automation scripts | `enterprise/scripts/*.py` | telemetry (file count) |
| Build system | `Makefile` | telemetry (existence) |

## Cadence

Every release — computed by `enterprise/scripts/kpi_compute.py`.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 7.0 | No action |
| Yellow | 7.0 > score >= 4.0 | Review automation gaps |
| Red | score < 4.0 | Release blocked |

**Floor:** 4.0
**Max drop:** 1.0

## Failure Modes / Gaming Risks

- **False-high:** Many trivial or no-op workflow files inflate count.
- **False-low:** Consolidating workflows into fewer files lowers count despite equal coverage.
- **Gaming:** Creating empty YAML files. Mitigated by CI execution validation.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | Deployment Frequency (partial — automation enables frequency) |
| ISO/IEC 25010 | Maintainability (Testability), Performance Efficiency (Time Behaviour) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
