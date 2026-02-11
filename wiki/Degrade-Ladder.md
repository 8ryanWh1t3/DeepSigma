# Degrade Ladder

A degrade ladder is a controlled response to runtime physics.

Example ladder:
`cache_bundle → rules_only → hitl → abstain`

Triggers:
- deadline pressure (remaining time)
- tail latency/jitter
- TTL/TOCTOU breaches
- verifier fail/inconclusive

Implementation scaffold:
- `engine/degrade_ladder.py`
- `engine/supervisor_scaffold.py`
