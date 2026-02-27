# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **YELLOW** (RCF=0.85, RL_open=159)
- PCR: **extreme** (CCF=0.7, CL14=687)

## Edition Metrics
- CORE: TEC=345.0 | C-TEC=205.27 | KPI=1.0
- ENTERPRISE: TEC=1425.4 | C-TEC=848.11 | KPI=1.0
- TOTAL: TEC=18307.2 | C-TEC=10892.78 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  8714.2 hrs | $1307134
- Base: 10892.8 hrs | $1633917
- High: 14705.3 hrs | $2205788

### Executive @ $225/hr
- Low:  8714.2 hrs | $1960700
- Base: 10892.8 hrs | $2450876
- High: 14705.3 hrs | $3308682

### Public Sector Fully Burdened @ $275/hr
- Low:  8714.2 hrs | $2396412
- Base: 10892.8 hrs | $2995514
- High: 14705.3 hrs | $4043945

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
