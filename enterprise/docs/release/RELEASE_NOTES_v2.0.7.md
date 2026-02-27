# Release Notes - v2.0.7 — Nonlinear Stability + Credibility Hardening

## Highlights

- Introduced System Stability Index (SSI) — 0-100 composite detecting unsustainable KPI swings.
- Added drift acceleration detection (second derivative of KPI movements).
- Security proof pack v2 with integrity-chain-aware gate.
- Stale artifact kill-switch preventing stale releases.
- 392 tests. Issues #314-#317 + #337-#339 closed. Epics #311 + #340 closed.

## System Stability Index (SSI)

- `SSI = 0.35*Volatility + 0.30*DriftAccel + 0.20*Authority + 0.15*Economic`
- Gates: PASS >= 70, WARN >= 55, FAIL < 55.
- Monte Carlo simulation for confidence bands.
- Stability-adjusted roadmap forecasting.
- Artifacts: `stability_v2.0.7.json`, `stability_simulation_v2.0.7.json`, `nonlinear_stability_report.md`.

## TEC Sensitivity Analysis

- Economic fragility assessment: how C-TEC costs shift when RCF/CCF change by one tier.
- Cost volatility index (stddev/mean), sensitivity bands, economic fragility score (0-100).
- Artifacts: `tec_sensitivity.json`, `tec_sensitivity_report.md`.

## Security Proof Pack v2

- Integrity-chain-aware security gate replacing the earlier stub.
- Four checks: key lifecycle documentation, crypto proof validity, seal chain integrity, contract fingerprint consistency.
- Artifacts: `security_proof_pack.json`, enriched `SECURITY_GATE_REPORT.md`.

## Stale Artifact Kill-Switch

- CI gate preventing stale or missing release artifacts.
- Five checks: version match (pyproject vs VERSION.txt), current-version radar exists, badge freshness (<7 days), history appended, contract fingerprint match.
- Artifact: `scripts/verify_release_artifacts.py`.

## Additional Changes

- Banded radar rendering — confidence band envelope (low/high shaded polygon) on KPI radar charts.
- KPI eligibility tier CI validation — gate verifying every KPI has an explicit tier declaration.
- Policy version aligned to GOV-2.0.7.

## KPI Scorecard (v2.0.7)

| KPI | v2.0.6 | v2.0.7 | Delta |
|-----|--------|--------|-------|
| technical_completeness | 10.0 | 10.0 | 0.0 |
| automation_depth | 10.0 | 10.0 | 0.0 |
| authority_modeling | 6.0 | 6.0 | 0.0 |
| enterprise_readiness | 10.0 | 10.0 | 0.0 |
| scalability | 5.38 | 5.38 | 0.0 |
| data_integration | 10.0 | 10.0 | 0.0 |
| economic_measurability | 4.88 | 4.88 | 0.0 |
| operational_maturity | 10.0 | 10.0 | 0.0 |

## Operational Notes

- New make targets: `make stability`, `make tec-sensitivity`, `make security-gate`, `make verify-release-artifacts`.
- Mermaid diagram 20 (Stability & Credibility Pipeline) added to canonical set.
- README, wiki, FAQ, glossary updated with SSI, sensitivity, proof pack, and kill-switch docs.
