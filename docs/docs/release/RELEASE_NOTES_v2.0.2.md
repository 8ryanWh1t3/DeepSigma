# Release Notes — v2.0.2 (Pilot)

## What this release proves
- Deterministic pilot Coherence Index (CI) computation from repo state (`scripts/compute_ci.py`)
- Repo-native workflow: Decisions (DLR), Assumptions, Drift, Patches + reports in `pilot/reports/`
- Governance scaffolding + GitHub-native ops patterns

## What is NOT included (pilot boundary)
- Enterprise SSO/RBAC hardening
- "Plug-and-play" enterprise connectors with SLAs
- Production security posture guarantees (unless separately scoped)

## Pilot success criteria (minimum)
- PASS→FAIL→PASS drill reproducible in < 5 minutes (`make pilot-in-a-box`)
- PR gate enforced (CI must pass to merge) via required checks
- WHY-60s challenge completed by 2 new users

## Assets
- `pilot/` reference dataset
- `scripts/compute_ci.py`
- CI reports: `pilot/reports/ci_report.{json,md}`
