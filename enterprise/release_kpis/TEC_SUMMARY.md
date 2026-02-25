# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=570)

## Edition Metrics
- CORE: TEC=105.6 | C-TEC=73.92 | KPI=1.0
- ENTERPRISE: TEC=1227.8 | C-TEC=859.46 | KPI=1.0
- TOTAL: TEC=2025.6 | C-TEC=1417.92 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  1134.3 hrs | $170150
- Base: 1417.9 hrs | $212688
- High: 1914.2 hrs | $287129

### Executive @ $225/hr
- Low:  1134.3 hrs | $255226
- Base: 1417.9 hrs | $319032
- High: 1914.2 hrs | $430693

### DoD Fully Burdened @ $275/hr
- Low:  1134.3 hrs | $311942
- Base: 1417.9 hrs | $389928
- High: 1914.2 hrs | $526403

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
