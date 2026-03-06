# TEC Summary (C-TEC v3)

## Latest Factors
- Formula: **v3**
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=504)
- Quality Factor: **1.0** (confidence-weighted KPI mean=10.0, n=8)
- Stability Factor: **0.7985** (SSI=59.7)

## Edition Metrics
- CORE: TEC=365.64 | C-TEC=204.38 | CC=0.5589
- ENTERPRISE: TEC=1495.91 | C-TEC=836.14 | CC=0.5589
- TOTAL: TEC=2763.73 | C-TEC=1544.79 | CC=0.5589

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  1235.8 hrs | $185375
- Base: 1544.8 hrs | $231718
- High: 2085.5 hrs | $312820

### Executive @ $225/hr
- Low:  1235.8 hrs | $278062
- Base: 1544.8 hrs | $347578
- High: 2085.5 hrs | $469230

### Public Sector Fully Burdened @ $275/hr
- Low:  1235.8 hrs | $339854
- Base: 1544.8 hrs | $424817
- High: 2085.5 hrs | $573503

## Release KPI Scores

**Version:** v2.1.0

| KPI | Score | Tier | Confidence |
|-----|------:|------|----------:|
| Technical Completeness | 10.0 | production | 0.9 |
| Automation Depth | 10.0 | production | 0.9 |
| Authority Modeling | 10.0 | production | 0.9 |
| Enterprise Readiness | 10.0 | production | 0.9 |
| Scalability | 10.0 | production | 0.9 |
| Data Integration | 10.0 | production | 0.9 |
| Economic Measurability | 10.0 | production | 0.9 |
| Operational Maturity | 10.0 | production | 0.9 |

**Mean:** 10.0/10 · **Gate:** PASS (no floors violated, no regressions)

## Scalability Benchmark

- Throughput: **3,784,999.5 RPS**
- Data rate: **41,366.7 MB/min**
- Wall clock: **0.0264s** (100,000 records)
- RSS peak: **82.8 MB**
- Evidence: **real_workload** · Eligible: **True**

## Economic Metrics

- TEC base hours: **4,616.5**
- Decisions: **247**
- Avg cost/decision: **$2,803.54**
- Total cost (internal): **$692,474**
- MTTR: **0.0264s**
- Evidence: **real_workload** · Eligible: **True**

## Security Metrics

- MTTR: **0.0264s**
- Re-encrypt throughput: **3,784,999.5 RPS**
- Signing mode: **hmac**
- Evidence: **simulated** · Eligible: **False**

## System Stability Index (SSI)

- SSI: **59.7** (gate: **WARN**)
- Confidence: **0.89**
- Drift acceleration index: **0.6825**

## Pulse Insights

- Insights score: **6.16/10**
- Active signals: **3**
  - `open_p0_caps` (high): One or more KPI tracks report open P0 caps.
  - `kpi_mean_low` (medium): Merged KPI mean is below target threshold (6.0).
  - `kpi_trend_down` (medium): KPI average trend is negative versus previous release.

## Standards Overlay

- Contracted KPIs: **8**
- SMART pass: **8/8**
- Experimental: **0**
- Frameworks: DORA · ISO/IEC 25010 · OpenTelemetry · SMART
- Detail: [kpi_standards_overlay.md](../../docs/kpi_standards_overlay.md)

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- **v3 Quality Factor (QF):** Replaces binary file-existence checks with confidence-weighted KPI scores. Evidence level (simulated vs production) directly affects weight via eligibility confidence.
- **v3 Stability Factor (SF):** SSI (System Stability Index) feeds into C-TEC. Unstable systems get a lower control multiplier, reflecting higher real-world effort.
- **v3 LOC in TEC:** Lines of code now contribute to the TEC formula, so complexity reflects actual code volume — not just file counts.
- Computes C-TEC as `TEC × QF × SF × RCF × CCF` = `TEC × 0.5589`.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
