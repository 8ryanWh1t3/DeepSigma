# Health Summary (v2)

- Generated: 2026-03-09T14:13:25Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=664.32 | C-TEC=385.04 | KPI=1.0
- ENTERPRISE: TEC=1524.1 | C-TEC=883.37 | KPI=1.0
- TOTAL: TEC=3098.26 | C-TEC=1795.75 | KPI=-
- ICR: GREEN | RL_open=0
- PCR: extreme | CL14=199

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-03-02 | 184.58 | 819.93 | 1503.56 | GREEN | 0 | 699 |
| 2026-03-03 | 184.58 | 822.86 | 1506.49 | GREEN | 0 | 698 |
| 2026-03-04 | 184.58 | 825.75 | 1509.38 | GREEN | 0 | 679 |
| 2026-03-05 | 184.58 | 828.47 | 1512.1 | GREEN | 0 | 633 |
| 2026-03-06 | 204.38 | 836.14 | 1544.79 | GREEN | 0 | 504 |
| 2026-03-07 | 433.27 | 993.04 | 11107.34 | GREEN | 0 | 427 |
| 2026-03-09 | 385.04 | 883.37 | 1795.75 | GREEN | 0 | 199 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
