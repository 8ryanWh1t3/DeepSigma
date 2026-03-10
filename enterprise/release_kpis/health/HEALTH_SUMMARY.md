# Health Summary (v2)

- Generated: 2026-03-10T14:09:19Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=664.32 | C-TEC=440.05 | KPI=1.0
- ENTERPRISE: TEC=1527.73 | C-TEC=1011.97 | KPI=1.0
- TOTAL: TEC=3102.89 | C-TEC=2055.36 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: high | CL14=77

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-03 | 184.58 | 822.86 | 1506.49 | GREEN | 0 | 698 |
| 2026-03-04 | 184.58 | 825.75 | 1509.38 | GREEN | 0 | 679 |
| 2026-03-05 | 184.58 | 828.47 | 1512.1 | GREEN | 0 | 633 |
| 2026-03-06 | 204.38 | 836.14 | 1544.79 | GREEN | 0 | 504 |
| 2026-03-07 | 433.27 | 993.04 | 11107.34 | GREEN | 0 | 427 |
| 2026-03-09 | 385.04 | 883.37 | 1795.75 | GREEN | 0 | 199 |
| 2026-03-10 | 440.05 | 1011.97 | 2055.36 | GREEN | 0 | 77 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
