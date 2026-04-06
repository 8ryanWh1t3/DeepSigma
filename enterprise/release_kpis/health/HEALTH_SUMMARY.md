# Health Summary (v2)

- Generated: 2026-04-06T14:15:33Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=693.5 | C-TEC=574.22 | KPI=1.0
- ENTERPRISE: TEC=1602.51 | C-TEC=1326.87 | KPI=1.0
- TOTAL: TEC=3240.07 | C-TEC=2682.78 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: low | CL14=0

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-27 | 574.22 | 1308.63 | 2664.54 | GREEN | 0 | 15 |
| 2026-03-30 | 574.22 | 1311.67 | 2667.58 | GREEN | 0 | 2 |
| 2026-03-31 | 574.22 | 1314.72 | 2670.62 | GREEN | 0 | 2 |
| 2026-04-01 | 574.22 | 1317.75 | 2673.66 | GREEN | 0 | 0 |
| 2026-04-02 | 574.22 | 1320.79 | 2676.7 | GREEN | 0 | 0 |
| 2026-04-03 | 574.22 | 1323.83 | 2679.74 | GREEN | 0 | 0 |
| 2026-04-06 | 574.22 | 1326.87 | 2682.78 | GREEN | 0 | 0 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
