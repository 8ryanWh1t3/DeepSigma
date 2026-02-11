# Sealing & Episodes

A **DecisionEpisode** is the immutable audit unit.

Sealing rules:
- serialize episode (excluding `seal`)
- compute hash
- store `sealHash` + `sealedAt`

vNext stamping:
- `policy.policyPackId/version/hash`
- `degrade.step` + rationale

See:
- `specs/episode.schema.json`
- `tools/run_supervised.py`
