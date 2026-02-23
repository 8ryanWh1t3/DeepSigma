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

Time-Effort-Cost is published in three deterministic lenses from the same telemetry:

- Internal: `release_kpis/tec_internal.json`
- Executive: `release_kpis/tec_executive.json`
- DoD: `release_kpis/tec_dod.json`
- Summary: `release_kpis/TEC_SUMMARY.md`

C-TEC v1.0 adds intrinsic complexity signals:

- PR churn (`additions + deletions`)
- PR file spread (`changedFiles`)
- cross-subsystem touch (`security`, `authority`, `kpi`, `ci`)
- issue duration (`createdAt -> closedAt`)
- dependency/coordination references (`#issue` links)
