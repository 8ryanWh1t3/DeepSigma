# KPI Contract: Technical Completeness

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-001 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Confirms that core source code, test suites, CI pipelines, and packaging artifacts are present and structurally complete. Supports the release-readiness decision.

## Formula

```
points = 0
if src/core exists:          points += 2
if tests/ exists:            points += 2
if compute_ci.py present:    points += 2
if .github/workflows/ exist: points += 2
if pyproject.toml exists:    points += 2
score = min(points, 10.0)
```

Plain-English: One point-pair per critical infrastructure artifact, capped at 10.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Core source tree | `src/core/` | telemetry (directory existence) |
| Test directory | `tests/` | telemetry |
| CI compute script | `enterprise/scripts/compute_ci.py` | telemetry |
| Workflow directory | `.github/workflows/` | telemetry |
| Package config | `pyproject.toml` | telemetry |

## Cadence

Every release — computed by `enterprise/scripts/kpi_compute.py` via `make kpi`.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 8.0 | No action |
| Yellow | 8.0 > score >= 5.0 | Review missing artifacts |
| Red | score < 5.0 | Release blocked |

**Floor:** 5.0 (from `kpi_spec.yaml`)
**Max drop:** 1.0 per release

## Failure Modes / Gaming Risks

- **False-high:** Empty directories or stub files could satisfy existence checks without real content.
- **False-low:** Unlikely given binary existence checks.
- **Gaming:** Creating placeholder files. Mitigated by CI test-pass requirements and code review.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | N/A |
| ISO/IEC 25010 | Maintainability (Modularity), Functional Suitability (Completeness) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
