# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **YELLOW** (RCF=0.85, RL_open=159)
- PCR: **extreme** (CCF=0.7, CL14=687)

## Edition Metrics
- CORE: TEC=347.0 | C-TEC=206.47 | KPI=1.0
- ENTERPRISE: TEC=1518.4 | C-TEC=903.45 | KPI=1.0
- TOTAL: TEC=18425.2 | C-TEC=10962.99 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  8770.4 hrs | $1315559
- Base: 10963.0 hrs | $1644448
- High: 14800.0 hrs | $2220005

### Executive @ $225/hr
- Low:  8770.4 hrs | $1973338
- Base: 10963.0 hrs | $2466673
- High: 14800.0 hrs | $3330008

### Public Sector Fully Burdened @ $275/hr
- Low:  8770.4 hrs | $2411858
- Base: 10963.0 hrs | $3014822
- High: 14800.0 hrs | $4070010

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
