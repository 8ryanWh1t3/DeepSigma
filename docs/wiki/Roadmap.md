# Roadmap

Current roadmap is organized into four execution tracks.

## Track A — Credibility Hardening (v2.0.7)

- KPI confidence bands (score + uncertainty)
- KPI evidence-tier gating (simulated/real/production)
- Stale artifact kill-switch in CI
- Security posture proof-pack hardening

## Track B — Adoption Wedge (v2.0.8)

- `make try` 10-minute pilot mode
- Decision Office scaffolding templates
- Shareable pilot distribution pack

## Track C — Enterprise Integration (v2.1.0-pre)

- GitHub Issues -> DLR mapping
- SharePoint/Teams export mode
- Jira import/export adapter

## Track D — DISR Architecture Expansion (v2.1.0)

- Dual-mode crypto providers (local default + optional KMS)
- Authority-bound action contracts
- Streaming re-encrypt with checkpoint/resume
- Signed telemetry event chain and exportable audit pack

## Release Proof Requirements

- Version parity across `pyproject.toml`, release notes, and KPI artifacts
- Reproducible KPI pipeline output (`release_kpis/`)
- Security gate and issue-label gate passing
- Pilot evidence pack generated and linked

