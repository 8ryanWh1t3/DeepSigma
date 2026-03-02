# KPI Contract: Economic Measurability

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-007 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Validates ability to quantify cost-per-decision and effort economics from TEC/C-TEC pipelines. Supports budget justification and ROI decisions.

## Formula

```
score = 3.0  # base if metrics present
if mttr <= 300s:      score += 3  elif <= 600s: += 2  elif <= 1200s: += 1
if rps >= 1:          score += 2  elif >= 0.1: += 1
if mb_min >= 0.01:    score += 2  elif >= 0.001: += 1
score = min(score, 10.0)

# Eligibility gate:
if not (kpi_eligible and evidence_level == "real_workload"):
    score = min(score, 4.0)
```

Plain-English: Base of 3 (metrics present) plus tiered points for MTTR, throughput, and data rate. Hard cap at 4.0 unless backed by real workload evidence.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Economic metrics | `enterprise/release_kpis/economic_metrics.json` | CI artifact |
| TEC summary | `enterprise/release_kpis/TEC_SUMMARY.md` | CI artifact |
| TEC computation | `enterprise/scripts/tec_ctec.py` | telemetry |
| TEC estimate | `enterprise/scripts/tec_estimate.py` | telemetry |

## Cadence

Every release.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 5.0 | No action |
| Yellow | 5.0 > score >= 2.0 | Review economic model gaps |
| Red | score < 2.0 | Release blocked |

**Floor:** 2.0
**Max drop:** 1.0

## Failure Modes / Gaming Risks

- **False-high:** Economic metrics derived from synthetic benchmarks rather than real usage.
- **False-low:** Missing or stale economic_metrics.json.
- **Gaming:** Inflating decision counts to lower avg_cost_per_decision. Mitigated by TEC cross-validation.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | N/A |
| ISO/IEC 25010 | Maintainability (Analysability), Functional Suitability (Appropriateness) |
| OTel | N/A |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS\* · T:PASS · Net: PASS\* |
| SMART note | R passes via documented formula; TEC cost model involves manual assumptions |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
