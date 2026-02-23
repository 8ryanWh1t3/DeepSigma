# Release Notes — v2.0.4

## What this release proves
- Helm chart validation is now reliable in CI for kind-based installs.
- Release metadata is coherently advanced to `v2.0.4` / `GOV-2.0.4`.
- Repo Radar artifacts advance to a new release point with composite comparison preserved.

## Notable changes
- Fixed `kind-install-test` workflow rollout targeting to use release-label deployment waits.
- Removed external registry dependency for API image in kind Helm validation by building and loading a local CI image.
- Continued least-privilege workflow posture and sanitized health-path error exposure from prior security burndown.

## Governance/version updates
- Package version: `2.0.4`
- Policy version: `GOV-2.0.4`
- KPI release pointer: `release_kpis/VERSION.txt` -> `v2.0.4`

## Scope boundaries
- v2.0.4 is a release hardening update focused on CI reliability and release coherence.
- No new product surface area is introduced beyond existing pilot and scale validation paths.
