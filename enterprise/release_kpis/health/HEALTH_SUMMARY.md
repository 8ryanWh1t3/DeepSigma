# Health Summary (v2)

- Generated: 2026-04-21T14:54:12Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=693.5 | C-TEC=574.22 | KPI=1.0
- ENTERPRISE: TEC=1643.12 | C-TEC=1360.5 | KPI=1.0
- TOTAL: TEC=3280.68 | C-TEC=2716.41 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: low | CL14=9

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-04-13 | 574.22 | 1342.08 | 2697.99 | GREEN | 0 | 0 |
| 2026-04-14 | 574.22 | 1345.12 | 2701.03 | GREEN | 0 | 0 |
| 2026-04-15 | 574.22 | 1348.22 | 2704.13 | GREEN | 0 | 9 |
| 2026-04-16 | 574.22 | 1351.29 | 2707.2 | GREEN | 0 | 9 |
| 2026-04-17 | 574.22 | 1354.36 | 2710.27 | GREEN | 0 | 9 |
| 2026-04-20 | 574.22 | 1357.43 | 2713.34 | GREEN | 0 | 9 |
| 2026-04-21 | 574.22 | 1360.5 | 2716.41 | GREEN | 0 | 9 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
