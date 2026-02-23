# Release Notes — v2.0.4 (Pilot)

## What this release proves
- Pilot and chart validation workflows are stable under kind-based install tests.
- Release/version metadata can be advanced cleanly while preserving KPI composite history.

## Notable changes
- `kind-install-test` no longer depends on a hardcoded deployment name.
- Helm validation now builds and loads a local API image into kind to avoid GHCR pull failures.
- Policy and release metadata advanced to v2.0.4 / GOV-2.0.4.

## Pilot compatibility
- Existing pilot drills and governance docs remain intact.
- Repo Radar composite continues comparing current release against prior releases.
