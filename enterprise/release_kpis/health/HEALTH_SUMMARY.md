# Health Summary (v2)

- Generated: 2026-02-27T18:29:19Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=197.0 | C-TEC=117.21 | KPI=1.0
- ENTERPRISE: TEC=1235.6 | C-TEC=735.18 | KPI=1.0
- TOTAL: TEC=2216.0 | C-TEC=1318.52 | KPI=1.0
- ICR: YELLOW | RL_open=159
- PCR: extreme | CL14=687

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | TOTAL C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---:|---|---:|---:|
| 2026-02-24 | 56.28 | 849.66 | 1399.02 | GREEN | 0 | 570 |
| 2026-02-25 | 73.92 | 859.46 | 1417.92 | - | - | - |
| 2026-02-27 | 117.21 | 735.18 | 1318.52 | YELLOW | 159 | 687 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.

## Accuracy Notes

- `TOTAL` now measures full-repo scope, while `CORE` and `ENTERPRISE` stay edition-specific for boundary clarity.
- C-TEC is control-adjusted using current governance posture (`ICR -> RCF`) and current change pressure (`PCR/CL14 -> CCF`).
- Snapshot history provides time-series evidence, reducing one-off metric noise and making degradation/recovery explicit.
