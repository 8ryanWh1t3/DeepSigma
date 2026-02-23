# Release Notes — v2.0.2

## What this release proves
- Deterministic pilot Coherence Index computation (CI) from repo state (`scripts/compute_ci.py`)
- GitHub-native drift workflow: issue forms + PR gating + CI reporting
- Signature/determinism/admissibility gates present as workflow scaffolds
- Pilot artifacts: decisions, assumptions, drift, patches, and reports

## What is NOT included (pilot scope boundaries)
- Turnkey enterprise auth, SSO, data plane security hardening
- Production connector SLAs (SharePoint/Snowflake/etc.) without org-specific adapter work
- "Plug-and-play" dashboards beyond provided demo UI

## Pilot success criteria (minimum)
- PASS->FAIL->PASS drill reproducible in under 5 minutes
- PR gate enforced (CI must pass to merge) via required checks
- 60-second WHY retrieval challenge completed by 2 new users

## Notable assets
- `pilot/` reference dataset (DLR/Assumptions/Drift/Patches)
- `scripts/compute_ci.py` and `pilot/reports/ci_report.*`
- Workflows: `.github/workflows/coherence_ci.yml` and governance gates
