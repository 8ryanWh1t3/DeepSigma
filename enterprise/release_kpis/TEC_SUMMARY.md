# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=570)

## Edition Metrics
- CORE: TEC=316.2 | C-TEC=221.34 | KPI=1.0
- ENTERPRISE: TEC=1397.4 | C-TEC=978.18 | KPI=1.0
- TOTAL: TEC=18139.0 | C-TEC=12697.3 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  10157.8 hrs | $1523676
- Base: 12697.3 hrs | $1904595
- High: 17141.4 hrs | $2571203

### Executive @ $225/hr
- Low:  10157.8 hrs | $2285514
- Base: 12697.3 hrs | $2856892
- High: 17141.4 hrs | $3856805

### Public Sector Fully Burdened @ $275/hr
- Low:  10157.8 hrs | $2793406
- Base: 12697.3 hrs | $3491758
- High: 17141.4 hrs | $4713873

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
