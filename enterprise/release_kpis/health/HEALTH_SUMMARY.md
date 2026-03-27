# Health Summary (v2)

- Generated: 2026-03-27T14:17:38Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=693.5 | C-TEC=574.22 | KPI=1.0
- ENTERPRISE: TEC=1580.48 | C-TEC=1308.63 | KPI=1.0
- TOTAL: TEC=3218.05 | C-TEC=2664.54 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: low | CL14=15

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-19 | 516.8 | 1161.22 | 2378.55 | GREEN | 0 | 34 |
| 2026-03-20 | 574.22 | 1293.3 | 2649.2 | GREEN | 0 | 23 |
| 2026-03-23 | 574.22 | 1296.38 | 2652.28 | GREEN | 0 | 23 |
| 2026-03-24 | 574.22 | 1299.46 | 2655.37 | GREEN | 0 | 23 |
| 2026-03-25 | 574.22 | 1302.54 | 2658.45 | GREEN | 0 | 23 |
| 2026-03-26 | 574.22 | 1305.58 | 2661.48 | GREEN | 0 | 15 |
| 2026-03-27 | 574.22 | 1308.63 | 2664.54 | GREEN | 0 | 15 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
