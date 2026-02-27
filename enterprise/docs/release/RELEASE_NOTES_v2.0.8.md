# Release Notes - v2.0.8 — Scalability Evidence + SSI Recovery

## Highlights

- Scalability KPI lifted from 5.38 to 10.0 via CI-eligible benchmark infrastructure.
- Scalability regression gate preventing throughput regressions.
- Benchmark trend visualization for historical throughput tracking.
- SSI trajectory improving: 37.71 → 39.05.
- Issues #410-#412 closed.

## CI-Eligible Benchmark

- `reencrypt_benchmark.py --ci-mode` produces deterministic 100K-record DISR pipeline benchmark.
- Sets `kpi_eligible=true` and `evidence_level=real_workload`, uncapping scalability from the 4.0 simulated ceiling.
- Measures: throughput (records/sec), wall clock time, CPU time, peak RSS memory.
- Artifacts: `scalability_metrics.json`, `security_metrics.json`, `benchmark_history.json`, `benchmark_summary.json`.

## Scalability Regression Gate

- CI gate enforcing 80% throughput floor relative to previous benchmark.
- Requires `evidence_level` of `real_workload` or `ci_benchmark`.
- Prevents performance regressions from landing undetected.
- Artifact: `SCALABILITY_GATE_REPORT.md`.

## Benchmark Trend Visualization

- Historical throughput bar chart with 80% regression floor overlay.
- Markdown history table for quick reference.
- Artifacts: `benchmark_trend.png`, `benchmark_trend.svg`, `benchmark_trend.md`.

## SSI Recovery

- SSI improved from 37.71 (v2.0.7) to 39.05 by adding scalability evidence (+4.62) while holding all other KPIs stable.
- Drift acceleration remains at 1.0 due to historical oscillations in automation_depth (v2.0.3-v2.0.7).
- SSI >= 55 projected around v2.1.0 with continued stability-focused releases.

## KPI Scorecard (v2.0.8)

| KPI | v2.0.7 | v2.0.8 | Delta |
|-----|--------|--------|-------|
| technical_completeness | 10.0 | 10.0 | 0.0 |
| automation_depth | 10.0 | 10.0 | 0.0 |
| authority_modeling | 6.0 | 6.0 | 0.0 |
| enterprise_readiness | 10.0 | 10.0 | 0.0 |
| scalability | 5.38 | 10.0 | +4.62 |
| data_integration | 10.0 | 10.0 | 0.0 |
| economic_measurability | 4.88 | 4.88 | 0.0 |
| operational_maturity | 10.0 | 10.0 | 0.0 |

**KPI Gate:** 6/8 axes >= 7.0 (authority_modeling and economic_measurability still below threshold).

## Operational Notes

- New make targets: `make benchmark`, `make scalability-gate`, `make benchmark-trend`.
- Mermaid diagram 21 (Scalability Benchmark Pipeline) added to canonical set.
- README, wiki, FAQ, glossary updated with benchmark, regression gate, and SSI recovery docs.
