# Release Notes - v2.0.6

## Highlights
- Published release `v2.0.6` from `main`.
- Added deterministic TEC estimation outputs in `release_kpis/`:
  - `TEC_SUMMARY.md`
  - `tec_internal.json`
  - `tec_executive.json`
  - `tec_dod.json`
- Wired TEC generation into KPI pipeline (`make kpi`) and PR comment output.

## C-TEC v1.0 Upgrade
- Upgraded TEC to complexity-weighted TEC (C-TEC v1.0).
- Added complexity signals derived from observable repo friction:
  - PR diff size (additions + deletions)
  - files changed per PR
  - cross-subsystem touch (security/authority/kpi/ci)
  - issue duration (open to close)
  - dependency/reference count in issue body

## Operational Notes
- KPI and KPI gate workflows now install `PyYAML` for TEC/C-TEC execution.
- README, wiki, and mermaid docs updated to include TEC artifacts and navigation.
