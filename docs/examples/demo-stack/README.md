# Demo Stack (Scaffold)

This directory will host a 3-minute demo proving:
1) Good path → on-time + fresh → act → verify → seal
2) Freshness drift → degrade/abstain → drift
3) Unsafe action → blocked → drift
4) Tool spike → fallback/circuit breaker → drift

Implementations can be docker-compose based.


## Validate examples
Run:

```bash
pip install jsonschema pyyaml
python tools/validate_examples.py
```
