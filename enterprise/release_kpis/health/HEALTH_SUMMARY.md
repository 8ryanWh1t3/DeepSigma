# Health Summary (v2)

- Generated: 2026-03-11T14:13:16Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=664.32 | C-TEC=495.05 | KPI=1.0
- ENTERPRISE: TEC=1531.43 | C-TEC=1141.22 | KPI=1.0
- TOTAL: TEC=3106.6 | C-TEC=2315.04 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: medium | CL14=52

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-04 | 184.58 | 825.75 | 1509.38 | GREEN | 0 | 679 |
| 2026-03-05 | 184.58 | 828.47 | 1512.1 | GREEN | 0 | 633 |
| 2026-03-06 | 204.38 | 836.14 | 1544.79 | GREEN | 0 | 504 |
| 2026-03-07 | 433.27 | 993.04 | 11107.34 | GREEN | 0 | 427 |
| 2026-03-09 | 385.04 | 883.37 | 1795.75 | GREEN | 0 | 199 |
| 2026-03-10 | 440.05 | 1011.97 | 2055.36 | GREEN | 0 | 77 |
| 2026-03-11 | 495.05 | 1141.22 | 2315.04 | GREEN | 0 | 52 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
