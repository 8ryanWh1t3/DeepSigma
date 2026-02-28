# Release Notes — v2.1.0 "Decision Infrastructure Hardening"

**Date:** 2026-02-28
**Tag:** [v2.1.0](https://github.com/8ryanWh1t3/DeepSigma/releases/tag/v2.1.0)
**PyPI:** [deepsigma 2.1.0](https://pypi.org/project/deepsigma/2.1.0/)

---

## Release Gates

| Gate | Result |
|------|--------|
| All 8 KPIs >= 7.0 | PASS |
| SSI >= 55 | PASS (60.02) |
| drift_acceleration_index | 0.68 (WARN band) |
| Constitution Gate | PASS |
| Domain Scrub (GPE) | PASS |

## SSI Recovery

v2.1.0 completes the SSI recovery arc from v2.0.9 (SSI = 34.64, FAIL). Seven intermediate stability releases (v2.0.10–v2.0.16) shipped zero-drift KPI holds while closing 22 issues.

| Release | SSI | Drift Index | Gate |
|---------|-----|-------------|------|
| v2.0.9 | 34.64 | 1.00 | FAIL |
| v2.0.10 | 38.34 | 1.00 | FAIL |
| v2.0.11 | 41.22 | 1.00 | FAIL |
| v2.0.12 | 43.52 | 1.00 | FAIL |
| v2.0.13 | 46.84 | 1.00 | FAIL |
| v2.0.14 | 51.00 | 0.87 | FAIL |
| v2.0.15 | 54.50 | 0.79 | FAIL |
| v2.0.16 | 57.46 | 0.73 | WARN |
| **v2.1.0** | **60.02** | **0.68** | **WARN** |

## Issues Closed (29)

### Automation (v2.0.10)
- #401 — Pre-exec gate CI
- #402 — Idempotency guard
- #403 — Replay gate
- #395 — Automation depth epic

### Enterprise Hardening (v2.0.11)
- #407 — Deploy sanity (helm chart validation)
- #408 — Audit-neutral pack completeness
- #409 — Operator runbook + release checklist gate
- #397 — Enterprise readiness epic

### Schema + Determinism (v2.0.12)
- #417 — Schema version enforcement
- #416 — Input snapshot + environment fingerprint
- #418 — Replay reproducibility CI
- #400 — Technical completeness epic

### DISR Security (v2.0.13)
- #324 — Provider interface abstraction (5 providers)
- #326 — Streaming re-encrypt with checkpointing
- #327 — Signed telemetry event chain
- #313 — DISR architecture epic

### Evidence + Economic (v2.0.14)
- #393 — Evidence source binding schema
- #392 — Economic evidence ledger

### Safety (v2.0.15)
- #349 — Intent mutation detection

### Governance (v2.0.16)
- #332 — Scope freeze
- #358 — Milestone gate

### Reference Layer (v2.1.0)

- #461 — SSI trajectory
- #469 — Authority chain verification (`verify_chain`)
- #470 — Replay detection (`detect_replay`)
- #472 — Evidence source binding schema
- #473 — Economic cost ledger
- #474 — Intent mutation detection
- #475 — Schema version enforcement
- #476 — Reference layer badges

## Key Additions

- Authority ledger chain verification (`verify_chain`) + replay detection (`detect_replay`)
- Evidence source binding schema + validator
- Economic cost ledger with drift-to-patch tracking
- Intent mutation detection between sealed runs
- Schema version enforcement in CI
- Enterprise release checklist in OPS_RUNBOOK
- 6 new CI validation steps across determinism, enterprise, and replay workflows

## KPI Snapshot

| KPI | Value |
|-----|-------|
| technical_completeness | 10.0 |
| automation_depth | 10.0 |
| authority_modeling | 9.72 |
| enterprise_readiness | 10.0 |
| scalability | 10.0 |
| data_integration | 10.0 |
| economic_measurability | 10.0 |
| operational_maturity | 10.0 |
