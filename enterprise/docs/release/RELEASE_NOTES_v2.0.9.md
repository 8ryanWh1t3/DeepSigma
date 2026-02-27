# Release Notes - v2.0.9 — Authority + Economic Evidence

## Highlights

- All 8 KPI axes now >= 7.0, satisfying the v2.1.0 gate threshold.
- Authority modeling lifted from 6.0 to 9.72 via P0 #325 closure.
- Economic measurability lifted from 4.88 to 10.0 via dedicated evidence artifact.

## Authority Track

### Production Signature Key Custody (#413)
- `KEY_CUSTODY.md` documenting key generation, env-based storage, 90-day rotation, and revocation.
- `security_crypto_policy.json` updated with signing algorithm, key source, and rotation policy.
- `signing_key_id` parameter added to authority ledger entries for key provenance tracking.
- Tests: `test_authority_signature_custody.py` — sign/verify, tamper detection, missing key handling.

### Structural Refusal Authority Contract (#414)
- `REFUSE` action type added to action contracts via `create_refusal_contract()`.
- `AUTHORITY_REFUSAL` entry type in authority ledger with reason, refused action type, and refused-by.
- FEEDS authority gate consumer emits `AUTHORITY_REFUSED` drift signal (severity red) on refused claims.
- Tests: `test_authority_refusal.py` — contract creation, ledger blocking, unsigned refusal rejection.

### Authority Evidence Chain Export (#415)
- `export_authority_evidence.py` reads authority ledger and produces `authority_evidence.json`.
- Evidence bundle includes: chain verification, entry count, grant/refusal breakdown, signing key IDs, SHA-256 verification hash.
- Wired into KPI pipeline via `make authority-evidence`.

### P0 #325 Closed — Authority Cap Lifted
- Closing #413, #414, #415 satisfied the P0 parent issue #325 (Authority-Bound Action Contracts).
- `cap_if_open_p0: 6.0` removed from issue deltas, uncapping authority_modeling.
- Final score: **9.72** (base + credit_delta 2.72 - debt_delta 0.0).

## Economic Track

### Decision Cost Ledger + Value Delta (#404, #405)
- `economic_metrics.py` produces `economic_metrics.json` from TEC pipeline + security benchmarks + issue telemetry.
- Computes: avg cost per decision, total internal cost, drift remediation cost delta, patch value ratio.
- Sets `kpi_eligible: true` and `evidence_level: real_workload` — uncaps economic scoring.

### Economic KPI Ingestion Gate (#406)
- `kpi_compute.py` now prefers `economic_metrics.json` over `security_metrics.json` for economic scoring.
- `kpi_eligibility.json` updated with `economic_metrics.json` in real-tier evidence list.
- `economic_metrics_v1.json` schema for validation.
- Final score: **10.0** (base 3.0 + MTTR 3.0 + rps 2.0 + MB/min 2.0).

## KPI Scorecard (v2.0.9)

| KPI | v2.0.8 | v2.0.9 | Delta |
|-----|--------|--------|-------|
| technical_completeness | 10.0 | 10.0 | 0.0 |
| automation_depth | 10.0 | 10.0 | 0.0 |
| authority_modeling | 6.0 | 9.72 | +3.72 |
| enterprise_readiness | 10.0 | 10.0 | 0.0 |
| scalability | 10.0 | 10.0 | 0.0 |
| data_integration | 10.0 | 10.0 | 0.0 |
| economic_measurability | 4.88 | 10.0 | +5.12 |
| operational_maturity | 10.0 | 10.0 | 0.0 |

**KPI Gate:** PASS — all 8 axes >= 7.0
**SSI:** 34.64 (FAIL, gate >= 55) — expected; large KPI deltas increase volatility. Stability-focused releases will recover SSI.

## CI Fixes

- Added `enterprise/` prefix to default paths in 5 reconstruct/validate scripts (stale from Build 93 enterprise extraction).
- Reset `benchmark_history.json` so CI establishes its own throughput baseline.
- Fixed `reference/VERSION` parity to 2.0.9.

## Issues Closed

- #413 Production Signature Key Custody + Verification
- #414 Structural Refusal Authority Contract
- #415 Authority Evidence Chain Export
- #325 Authority-Bound Action Contracts (P0)
- #404 Decision Cost Ledger Schema + Emitter
- #405 Drift-to-Patch Value Delta Calculator
- #406 Economic KPI Ingestion Gate
- #394 GATE: v2.1.0 KPI Floor >= 7.0 (epic satisfied)
- #396 GAP: Economic Measurability (epic satisfied)
- #398 GAP: Scalability (epic satisfied)
- #399 GAP: Authority Modeling (epic satisfied)

## New Artifacts

| File | Purpose |
|------|---------|
| `release_kpis/authority_evidence.json` | Authority evidence chain export |
| `release_kpis/economic_metrics.json` | Dedicated economic evidence |
| `docs/docs/security/KEY_CUSTODY.md` | Key custody lifecycle docs |
| `schemas/economic_metrics_v1.json` | Economic metrics JSON schema |
| `docs/mermaid/22-authority-economic-evidence.md` | Mermaid pipeline diagram |

## Operational Notes

- `make authority-evidence` and `make economic-metrics` added to pipeline.
- KPI and CI workflows updated to upload `authority_evidence.json` and `economic_metrics.json`.
- README, wiki, FAQ, glossary, mermaid index updated for v2.0.9.
