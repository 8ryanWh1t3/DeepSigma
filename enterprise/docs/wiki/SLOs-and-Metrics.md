# SLOs & Metrics

Recommended SLOs:

- P99 end-to-end ≤ decisionWindowMs
- freshness compliance ≥ 99% (TTL/TOCTOU)
- verifier pass rate ≥ target
- drift recurrence trending down
- median “why retrieval” ≤ 60s (via MG)

Export via OpenTelemetry where possible.

## Repo Radar KPI

- Gate report: `release_kpis/KPI_GATE_REPORT.md`
- Label gate: `release_kpis/ISSUE_LABEL_GATE_REPORT.md`
- Trend: `release_kpis/kpi_trend.png`
- Composite: `release_kpis/radar_composite_latest.png`

## TEC / C-TEC (ROM)

See **[TEC and C-TEC](TEC-and-C-TEC)** for the full methodology, formulas, governance factors, and output artifacts.
