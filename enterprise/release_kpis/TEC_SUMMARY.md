# TEC Summary (C-TEC v3)

## Latest Factors
- Formula: **v3**
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **medium** (CCF=0.9, CL14=32)
- Quality Factor: **1.0** (confidence-weighted KPI mean=10.0, n=8)
- Stability Factor: **0.828** (SSI=65.6)

## Edition Metrics
- CORE: TEC=693.5 | C-TEC=516.8 | CC=0.7452
- ENTERPRISE: TEC=1550.74 | C-TEC=1155.61 | CC=0.7452
- TOTAL: TEC=3180.3 | C-TEC=2369.96 | CC=0.7452

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  1896.0 hrs | $284395
- Base: 2370.0 hrs | $355494
- High: 3199.4 hrs | $479917

### Executive @ $225/hr
- Low:  1896.0 hrs | $426593
- Base: 2370.0 hrs | $533241
- High: 3199.4 hrs | $719875

### Public Sector Fully Burdened @ $275/hr
- Low:  1896.0 hrs | $521391
- Base: 2370.0 hrs | $651739
- High: 3199.4 hrs | $879848

## Release KPI Scores

**Version:** v2.1.3

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

- Throughput: **3,232,593.1 RPS**
- Data rate: **35,329.4 MB/min**
- Wall clock: **0.0309s** (100,000 records)
- RSS peak: **84.1 MB**
- Evidence: **real_workload** · Eligible: **True**

## Economic Metrics

- TEC base hours: **4,396.3**
- Decisions: **247**
- Avg cost/decision: **$2,669.83**
- Total cost (internal): **$659,448**
- MTTR: **0.0309s**
- Evidence: **real_workload** · Eligible: **True**

## Security Metrics

- MTTR: **0.0309s**
- Re-encrypt throughput: **3,232,593.1 RPS**
- Signing mode: **hmac**
- Evidence: **simulated** · Eligible: **False**

## System Stability Index (SSI)

- SSI: **65.6** (gate: **WARN**)
- Confidence: **0.89**
- Drift acceleration index: **0.5641**

## Pulse Insights

- Insights score: **7.0/10**
- Active signals: **0**

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
- Computes C-TEC as `TEC × QF × SF × RCF × CCF` = `TEC × 0.7452`.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
