# TEC Summary (C-TEC v3)

## Latest Factors
- Formula: **v3**
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **low** (CCF=1.0, CL14=9)
- Quality Factor: **1.0** (confidence-weighted KPI mean=10.0, n=8)
- Stability Factor: **0.828** (SSI=65.6)

## Edition Metrics
- CORE: TEC=693.5 | C-TEC=574.22 | CC=0.828
- ENTERPRISE: TEC=1646.82 | C-TEC=1363.57 | CC=0.828
- TOTAL: TEC=3284.39 | C-TEC=2719.48 | CC=0.828

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  2175.6 hrs | $326338
- Base: 2719.5 hrs | $407922
- High: 3671.3 hrs | $550695

### Executive @ $225/hr
- Low:  2175.6 hrs | $489506
- Base: 2719.5 hrs | $611883
- High: 3671.3 hrs | $826042

### Public Sector Fully Burdened @ $275/hr
- Low:  2175.6 hrs | $598286
- Base: 2719.5 hrs | $747857
- High: 3671.3 hrs | $1009607

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
- Computes C-TEC as `TEC × QF × SF × RCF × CCF` = `TEC × 0.828`.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
