# Health Summary (v2)

- Generated: 2026-03-03T14:06:32Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=330.22 | C-TEC=184.58 | KPI=1.0
- ENTERPRISE: TEC=1472.16 | C-TEC=822.86 | KPI=1.0
- TOTAL: TEC=2695.22 | C-TEC=1506.49 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: extreme | CL14=698

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-02-24 | 56.28 | 849.66 | 1399.02 | GREEN | 0 | 570 |
| 2026-02-25 | 73.92 | 859.46 | 1417.92 | - | - | - |
| 2026-02-27 | 206.47 | 903.45 | 10962.99 | YELLOW | 159 | 687 |
| 2026-03-01 | 364.28 | 1123.78 | 13111.7 | GREEN | 0 | 678 |
| 2026-03-02 | 184.58 | 819.93 | 1503.56 | GREEN | 0 | 699 |
| 2026-03-03 | 184.58 | 822.86 | 1506.49 | GREEN | 0 | 698 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
