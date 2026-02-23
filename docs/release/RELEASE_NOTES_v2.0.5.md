# Release Notes — v2.0.5

## What this release proves
- DISR pilot lane is complete end-to-end: authority-gated rotation, signed security events, recovery drill, and measurable benchmark telemetry.
- Repo Radar can ingest security and scalability metrics from deterministic local artifacts.
- Release metadata is coherently advanced to `v2.0.5` / `GOV-2.0.5`.

## Notable changes
- Added authority-modeled key rotation approvals with signed `AUTHORIZED_KEY_ROTATION` events and chained authority ledger entries.
- Added security misuse gating workflow and scanner (`make security-gate`) with report artifacts.
- Added 10-minute DISR drill and deterministic demo runner (`make security-demo`).
- Added deterministic re-encrypt benchmark (`make reencrypt-benchmark`) with CPU/RAM/wall-clock throughput telemetry.
- Added unit coverage for DISR keyring/rotation/reencrypt and KPI metric parsing.

## Governance/version updates
- Package version: `2.0.5`
- Policy version: `GOV-2.0.5`
- KPI release pointer: `release_kpis/VERSION.txt` -> `v2.0.5`

## Scope boundaries
- v2.0.5 is a DISR completion and evidence hardening release.
- It does not introduce new customer-specific integrations or production SSO/RBAC posture.
