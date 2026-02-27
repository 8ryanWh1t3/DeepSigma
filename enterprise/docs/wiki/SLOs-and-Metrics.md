# SLOs & Metrics

Recommended SLOs:

- P99 end-to-end ≤ decisionWindowMs
- freshness compliance ≥ 99% (TTL/TOCTOU)
- verifier pass rate ≥ target
- drift recurrence trending down
- median “why retrieval” ≤ 60s (via MG)

Export via OpenTelemetry where possible.

## Coherence Metrics

Four composable metric points computed from DLR, RS, DS, and MG pipelines. Available via `coherence metrics` CLI or `MetricsCollector` API.

| Metric | Unit | Description |
| --- | --- | --- |
| `coherence_score` | score (0-100) | Weighted composite of policy adherence, outcome health, drift control, and memory completeness |
| `drift_density` | ratio | Drift signals divided by episode count. Lower is better. Zero means no drift. |
| `authority_coverage` | ratio | Fraction of claims with a valid authority grant. 1.0 = full coverage. |
| `memory_coverage` | ratio | Fraction of expected episodes in the memory graph. 1.0 = all decisions remembered. |

Generate site data files: `make site-content` produces `docs/site/data/demo.json` and `docs/site/data/metrics.json`.

## Repo Radar KPI

- Gate report: `release_kpis/KPI_GATE_REPORT.md`
- Label gate: `release_kpis/ISSUE_LABEL_GATE_REPORT.md`
- Scalability gate: `release_kpis/SCALABILITY_GATE_REPORT.md`
- Trend: `release_kpis/kpi_trend.png`
- Composite: `release_kpis/radar_composite_latest.png`
- Benchmark trend: `release_kpis/benchmark_trend.png`

## Scalability Benchmark Metrics

Produced by `make benchmark` (re-encrypt benchmark with `--ci-mode`). Stored in `release_kpis/scalability_metrics.json`.

| Metric | Unit | Description |
| --- | --- | --- |
| `throughput_records_per_second` | rps | Records processed per second |
| `throughput_mb_per_minute` | MB/min | Data throughput rate |
| `wall_clock_seconds` | seconds | Wall clock time for full benchmark |
| `cpu_seconds` | seconds | CPU time consumed |
| `rss_peak_bytes` | bytes | Peak resident set size |
| `scalability_score` | score (0-10) | Composite: base(2) + MTTR(0-3) + throughput(0-3) + MB/min(0-2) |
| `kpi_eligible` | boolean | Whether evidence counts for KPI uplift |
| `evidence_level` | string | `real_workload`, `ci_benchmark`, or `simulated` |

Regression gate (`make scalability-gate`): throughput must stay >= 80% of previous run.

## System Stability Index (SSI)

Nonlinear stability metric (0-100) tracking KPI volatility and drift acceleration across releases.

| Component | Weight | Source |
| --- | --- | --- |
| Volatility Score | 35% | Mean absolute KPI delta across releases |
| Drift Acceleration Score | 30% | Second derivative of KPI movements |
| Authority Score | 20% | authority_modeling KPI (normalized) |
| Economic Score | 15% | economic_measurability KPI (normalized) |

Gates: PASS >= 70, WARN >= 55, FAIL < 55. Report: `release_kpis/nonlinear_stability_report.md`.

## TEC / C-TEC (ROM)

See **[TEC and C-TEC](TEC-and-C-TEC)** for the full methodology, formulas, governance factors, and output artifacts.
