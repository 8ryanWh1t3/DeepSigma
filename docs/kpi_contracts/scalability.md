# KPI Contract: Scalability

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-005 |
| **KPI_VERSION** | 1.0 |
| **Status** | Active |
| **Owner** | Maintainer (DRI) |

## Intent

Validates system throughput and recovery performance under load. Supports capacity planning and SLA decisions.

## Formula

```
score = 2.0
if mttr <= 300s:   score += 3  elif <= 600s: += 2  elif <= 1200s: += 1
if rps >= 5000:    score += 5  elif >= 1000: += 4  elif >= 100: += 2
if mb_min >= 500:  score += 3  elif >= 100: += 2   elif >= 10: += 1
score = min(score, 10.0)

# Eligibility gate:
if not (kpi_eligible and evidence_level == "real_workload"):
    score = min(score, 4.0)
```

Plain-English: Base of 2 plus tiered points for MTTR, throughput RPS, and MB/min. Hard cap at 4.0 unless backed by real workload evidence.

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| Scalability metrics | `enterprise/release_kpis/scalability_metrics.json` | CI artifact (benchmark output) |
| Benchmark script | `enterprise/scripts/reencrypt_benchmark.py` | telemetry |

## Cadence

Every release — benchmark runs in CI pipeline.

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= 7.0 | No action |
| Yellow | 7.0 > score >= 3.0 | Investigate regressions |
| Red | score < 3.0 | Release blocked |

**Floor:** 3.0
**Max drop:** 1.0
**Regression gate:** throughput must stay >= 80% of previous run.

## Failure Modes / Gaming Risks

- **False-high:** Benchmark runs on trivially small datasets. Mitigated by minimum record-count requirement (100K).
- **False-low:** CI runner resource contention causing lower throughput.
- **Gaming:** Tuning benchmark parameters to inflate RPS. Mitigated by fixed benchmark config in repo.

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | N/A |
| ISO/IEC 25010 | Performance Efficiency (Time Behaviour, Resource Utilisation, Capacity) |
| OTel | Partial — `deepsigma.benchmark.throughput_rps` (gauge) |
| SMART | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · Net: PASS |

## Change History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial contract |
