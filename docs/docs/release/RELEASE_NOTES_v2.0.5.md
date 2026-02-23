# Release Notes — v2.0.5 (Pilot)

## What this release proves
- DISR pilot work is complete across authority modeling, detectability gates, recovery drills, and benchmark telemetry.
- Repo Radar can consume deterministic security/scalability metrics from release artifacts.

## Notable changes
- Authority-gated key rotation with signed `AUTHORIZED_KEY_ROTATION` events and authority ledger output.
- Security gate workflow and misuse scanner integrated into CI.
- 10-minute DISR demo and re-encrypt benchmark scripts wired to Make targets.
- KPI telemetry parsing extended for `economic_measurability` and `scalability` when metric files are present.

## Pilot compatibility
- Existing pilot drills and governance docs remain intact.
- Pilot pack now includes DISR security and scalability evidence artifacts when generated.
