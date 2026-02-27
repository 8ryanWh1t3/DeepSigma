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
- Trend: `release_kpis/kpi_trend.png`
- Composite: `release_kpis/radar_composite_latest.png`

## TEC / C-TEC (ROM)

See **[TEC and C-TEC](TEC-and-C-TEC)** for the full methodology, formulas, governance factors, and output artifacts.
