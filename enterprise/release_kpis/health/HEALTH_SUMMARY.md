# Health Summary (v2)

- Generated: 2026-02-24T13:17:46Z
- Source: `enterprise/release_kpis/health`

## Latest

- CORE: TEC=80.4 | C-TEC=56.28 | KPI=1.0
- ENTERPRISE: TEC=1204.4 | C-TEC=843.08 | KPI=1.0
- ICR: GREEN | RL_open=0
- PCR: extreme | CL14=570

## 7-Day Trend

| Date | CORE C-TEC | ENT C-TEC | ICR | RL_open | CL14 |
|---|---:|---:|---|---:|---:|
| 2026-02-24 | 56.28 | 843.08 | GREEN | 0 | 570 |

## Enforcement Signal

- Rule: if C-TEC drops while TEC rises across snapshots, treat as unmanaged complexity drift.
- Action: open drift event + patch plan, freeze net-new capability until control recovers.
