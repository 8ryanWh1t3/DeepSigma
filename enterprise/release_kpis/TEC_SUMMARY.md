# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=678)

## Edition Metrics
- CORE: TEC=520.4 | C-TEC=364.28 | KPI=1.0
- ENTERPRISE: TEC=1605.4 | C-TEC=1123.78 | KPI=1.0
- TOTAL: TEC=18731.0 | C-TEC=13111.7 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  10489.4 hrs | $1573404
- Base: 13111.7 hrs | $1966755
- High: 17700.8 hrs | $2655119

### Executive @ $225/hr
- Low:  10489.4 hrs | $2360106
- Base: 13111.7 hrs | $2950132
- High: 17700.8 hrs | $3982679

### Public Sector Fully Burdened @ $275/hr
- Low:  10489.4 hrs | $2884574
- Base: 13111.7 hrs | $3605718
- High: 17700.8 hrs | $4867719

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
