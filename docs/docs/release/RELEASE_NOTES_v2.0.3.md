# Release Notes — v2.0.3 (Pilot)

## What this release proves
- Security burndown execution can be carried through to green CodeQL on `main`
- Path expression risk surface is reduced via deterministic slugged path keys
- IRIS API responses are normalized and sanitized for safer operator-facing outputs

## Notable changes
- Hardened path mapping in governance, tenancy, credibility, mesh, and exhaust modules
- Tightened API output shaping for IRIS endpoints
- Advanced release and governance version metadata to v2.0.3 / GOV-2.0.3

## Pilot compatibility
- Existing pilot workflows and drills remain intact
- Legacy episode filenames continue to resolve via fallback lookup behavior in exhaust API
