# Degrade Ladder Engine

A degrade ladder converts runtime physics into controlled behavior.

Inputs:
- deadline pressure (remaining ms)
- tail latency (P99) and jitter
- TTL/TOCTOU freshness
- verifier results

Outputs:
- degrade step (cache_bundle → rules_only → HITL → abstain)
- machine-readable rationale
