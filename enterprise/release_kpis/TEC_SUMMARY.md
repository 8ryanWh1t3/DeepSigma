# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **YELLOW** (RCF=0.85, RL_open=159)
- PCR: **extreme** (CCF=0.7, CL14=687)

## Edition Metrics
- CORE: TEC=197.0 | C-TEC=117.21 | KPI=1.0
- ENTERPRISE: TEC=1235.6 | C-TEC=735.18 | KPI=1.0
- TOTAL: TEC=2216.0 | C-TEC=1318.52 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  1054.8 hrs | $158222
- Base: 1318.5 hrs | $197778
- High: 1780.0 hrs | $267000

### Executive @ $225/hr
- Low:  1054.8 hrs | $237334
- Base: 1318.5 hrs | $296667
- High: 1780.0 hrs | $400500

### Public Sector Fully Burdened @ $275/hr
- Low:  1054.8 hrs | $290074
- Base: 1318.5 hrs | $362593
- High: 1780.0 hrs | $489501

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
