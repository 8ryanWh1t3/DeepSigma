# Release Notes — v2.0.3

## What this release proves
- Security burndown is operationally executable in GitHub-native flow
- Path handling now avoids direct identifier-to-filesystem mapping by using deterministic slugged keys
- IRIS API responses are fixed-shape and sanitized to avoid traceback leakage

## Notable changes
- Updated path safety across:
  - `src/governance/audit.py`
  - `src/governance/telemetry.py`
  - `src/tenancy/policies.py`
  - `src/credibility_engine/store.py`
  - `src/mesh/logstore.py`
  - `src/mesh/transport.py`
  - `dashboard/server/exhaust_api.py`
- Strengthened IRIS API return shaping:
  - `dashboard/server/api.py`
  - `dashboard/api_server.py`

## Governance/version updates
- Package version: `2.0.3`
- Policy version: `GOV-2.0.3`
- Changelog updated with a dedicated v2.0.3 entry

## Scope boundaries
- v2.0.3 is a hardening and release coherence update; it does not introduce new product surface area beyond existing pilot workflows.
