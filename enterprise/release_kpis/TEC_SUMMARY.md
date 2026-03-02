# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=678)

## Edition Metrics
- CORE: TEC=520.4 | C-TEC=364.28 | KPI=1.0
- ENTERPRISE: TEC=1605.4 | C-TEC=1123.78 | KPI=1.0
- TOTAL: TEC=18754.6 | C-TEC=13128.22 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  10502.6 hrs | $1575386
- Base: 13128.2 hrs | $1969233
- High: 17723.1 hrs | $2658465

### Executive @ $225/hr
- Low:  10502.6 hrs | $2363080
- Base: 13128.2 hrs | $2953850
- High: 17723.1 hrs | $3987697

### Public Sector Fully Burdened @ $275/hr
- Low:  10502.6 hrs | $2888208
- Base: 13128.2 hrs | $3610260
- High: 17723.1 hrs | $4873852

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
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
