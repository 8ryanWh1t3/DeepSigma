# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **YELLOW** (RCF=0.85, RL_open=159)
- PCR: **extreme** (CCF=0.7, CL14=687)

## Edition Metrics
- CORE: TEC=345.0 | C-TEC=205.27 | KPI=1.0
- ENTERPRISE: TEC=1443.6 | C-TEC=858.94 | KPI=1.0
- TOTAL: TEC=18334.0 | C-TEC=10908.73 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  8727.0 hrs | $1309048
- Base: 10908.7 hrs | $1636310
- High: 14726.8 hrs | $2209018

### Executive @ $225/hr
- Low:  8727.0 hrs | $1963571
- Base: 10908.7 hrs | $2454464
- High: 14726.8 hrs | $3313527

### Public Sector Fully Burdened @ $275/hr
- Low:  8727.0 hrs | $2399921
- Base: 10908.7 hrs | $2999901
- High: 14726.8 hrs | $4049866

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
