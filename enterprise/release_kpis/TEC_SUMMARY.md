# TEC Summary (C-TEC v2)

## Latest Factors
- ICR: **GREEN** (RCF=1.0, RL_open=0)
- PCR: **extreme** (CCF=0.7, CL14=570)

## Edition Metrics
- CORE: TEC=80.4 | C-TEC=56.28 | KPI=1.0
- ENTERPRISE: TEC=1213.8 | C-TEC=849.66 | KPI=1.0
- TOTAL: TEC=1998.6 | C-TEC=1399.02 | KPI=1.0

## Tiers (from TOTAL C-TEC)
### Internal @ $150/hr
- Low:  1119.2 hrs | $167882
- Base: 1399.0 hrs | $209853
- High: 1888.7 hrs | $283302

### Executive @ $225/hr
- Low:  1119.2 hrs | $251824
- Base: 1399.0 hrs | $314780
- High: 1888.7 hrs | $424952

### DoD Fully Burdened @ $275/hr
- Low:  1119.2 hrs | $307784
- Base: 1399.0 hrs | $384730
- High: 1888.7 hrs | $519386

## Why This Is More Accurate
- Uses edition-scoped inventory plus full-repo `total` scope, so complexity is measured across actual shipped surfaces.
- Applies live governance factors (`RCF` from issue risk health, `CCF` from 14-day PR change load) instead of static effort-only multipliers.
- Computes C-TEC as control-adjusted complexity (`TEC x KPI_Coverage x RCF x CCF`), which reflects execution discipline, not just size.
- Produces deterministic daily snapshots (`ICR/PCR/TEC`) so trend direction is measurable and auditable over time.
