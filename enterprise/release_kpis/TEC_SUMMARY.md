# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=570)

## Edition Metrics
- CORE: TEC=345.0 | C-TEC=241.5 | KPI=1.0
- ENTERPRISE: TEC=1401.6 | C-TEC=981.12 | KPI=1.0
- TOTAL: TEC=18263.8 | C-TEC=12784.66 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  10227.7 hrs | $1534159
- Base: 12784.7 hrs | $1917699
- High: 17259.3 hrs | $2588894

### Executive @ $225/hr
- Low:  10227.7 hrs | $2301239
- Base: 12784.7 hrs | $2876548
- High: 17259.3 hrs | $3883340

### Public Sector Fully Burdened @ $275/hr
- Low:  10227.7 hrs | $2812625
- Base: 12784.7 hrs | $3515782
- High: 17259.3 hrs | $4746305

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
