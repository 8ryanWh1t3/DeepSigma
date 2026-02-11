# Drift → Patch

Drift is structured runtime failure/variance:
- time (deadline/p99)
- freshness (TTL/TOCTOU)
- fallback/bypass
- verify failures
- outcome anomalies

A DriftEvent should carry:
- type + severity
- fingerprint
- episode reference
- recommended patch type (future)

Patch workflow:
- drift triage → patch proposal → rollout → outcome monitoring
