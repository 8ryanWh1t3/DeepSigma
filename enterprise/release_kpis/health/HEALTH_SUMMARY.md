# Health Summary (v2)

- Generated: 2026-03-16T14:39:13Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=693.5 | C-TEC=516.8 | KPI=1.0
- ENTERPRISE: TEC=1546.99 | C-TEC=1152.82 | KPI=1.0
- TOTAL: TEC=3176.55 | C-TEC=2367.16 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: medium | CL14=32

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-07 | 433.27 | 993.04 | 11107.34 | GREEN | 0 | 427 |
| 2026-03-09 | 385.04 | 883.37 | 1795.75 | GREEN | 0 | 199 |
| 2026-03-10 | 440.05 | 1011.97 | 2055.36 | GREEN | 0 | 77 |
| 2026-03-11 | 495.05 | 1141.22 | 2315.04 | GREEN | 0 | 52 |
| 2026-03-12 | 495.05 | 1144.04 | 2320.09 | GREEN | 0 | 48 |
| 2026-03-13 | 495.05 | 1146.84 | 2322.89 | GREEN | 0 | 40 |
| 2026-03-16 | 516.8 | 1152.82 | 2367.16 | GREEN | 0 | 32 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
