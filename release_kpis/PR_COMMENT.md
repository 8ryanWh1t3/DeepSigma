## Repo Radar KPI — v2.0.6

![badge](release_kpis/badge_latest.svg)

**Radar:**
- PNG: `release_kpis/radar_v2.0.6.png`
- SVG: `release_kpis/radar_v2.0.6.svg`

**Composite Release Radar:**
- PNG: `release_kpis/radar_composite_latest.png`
- SVG: `release_kpis/radar_composite_latest.svg`
- Delta table: `release_kpis/radar_composite_latest.md`

**Roadmap Forecast:**
- Badge: `release_kpis/roadmap_badge.svg`
- Forecast: `release_kpis/roadmap_forecast.md`
- Timeline: `release_kpis/roadmap_timeline.svg`
- Scope gate: `release_kpis/ROADMAP_SCOPE_GATE_REPORT.md`

**Nonlinear Stability:**
- SSI JSON: `release_kpis/stability_v2.0.6.json`
- Simulation: `release_kpis/stability_simulation_v2.0.6.json`
- Report: `release_kpis/nonlinear_stability_report.md`

**Trend:**
- PNG: `release_kpis/kpi_trend.png`
- SVG: `release_kpis/kpi_trend.svg`

**Gates:**
- `release_kpis/KPI_GATE_REPORT.md`
- `release_kpis/ISSUE_LABEL_GATE_REPORT.md`

**Eligibility + Confidence:**
- Eligibility tiers: `governance/kpi_eligibility.json`
- KPI confidence: `release_kpis/kpi_confidence.json`
- KPI bands: `release_kpis/kpi_bands_v2.0.6.json`

**TEC (ROM):**
- Internal: 3098.0 hrs | $464,700
- Executive: 3098.0 hrs | $697,050
- DoD: 3098.0 hrs | $851,950
- Full detail: `release_kpis/TEC_SUMMARY.md`

**Notes:**
- Some KPIs are auto-derived from repo telemetry (tests, docs, workflows, pilot drills).
- Economic and Scalability are auto-derived from DISR metrics and capped by evidence eligibility (`kpi_eligible` / `evidence_level`).
- Authority Modeling remains manual/judgment-based until authority telemetry scoring is wired.

**Layer Coverage (Decision Infrastructure):**
- Layer_0_Intent: authority_modeling, operational_maturity
- Layer_1_AuditLogic: technical_completeness, enterprise_readiness
- Layer_2_PreExecution: automation_depth, authority_modeling
- Layer_3_RuntimeSafety: operational_maturity


## 🧩 Feature Coverage (Catalog)
- **Deterministic Governance Boundary**: 3 features
- **Intent Capture & Governance**: 3 features
- **Audit-Neutral Decision Logic**: 3 features
- **Deterministic Replay & Proof Chain**: 3 features
- **Repo Radar KPI System**: 2 features
- **Economic Measurability (TEC / C-TEC)**: 2 features
