# Reference Layer -- Summary

Autonomous agents suffer three structural failures: **decision amnesia**
(reasoning evaporates after execution), **authority vacuum** (no
verifiable chain from human intent to machine action), and **silent
drift** (behavior changes without detection or measurement).

A reference layer fixes all three. It seals every decision into a
tamper-evident episode log, binds each claim to a named authority grant
with scope and expiry, and emits typed drift signals whenever runtime
behavior diverges from baseline.

The result is a system where intent is explicit, authority is provable,
logic is auditable, and outcomes are sealed.

Proof -- baseline coherence from a three-episode session:

```json
{
  "overall_score": 90.0,
  "grade": "A",
  "dimensions": [
    {"name": "policy_adherence",    "score": 100.0},
    {"name": "outcome_health",      "score": 66.67},
    {"name": "drift_control",       "score": 100.0},
    {"name": "memory_completeness", "score": 100.0}
  ]
}
```

After drift injection the score drops to 85.75 (grade B). The change is
measured, recorded, and queryable. Nothing is lost. Nothing is silent.
