# Migration: v0.4 → v0.5

## The intentional break

v0.4 had drifted into governance, trust, authoritative publication, and CERPA integration. That work is not deleted, but it is no longer the VINCULUM core.

v0.5 redefines the canonical core as the P↔D Tension Engine.

## Removed from the core API

- signed governance bundles
- root trust anchors
- anti-rollback checkpointing
- authoritative repositories
- COMPOSER commit services
- CERPA APPLY guards
- authorization semantics

Keep a v0.4 environment/package if those capabilities are still needed as an integration experiment.

## New canonical API

```python
from vinculum import VinculumEngine, ingest_text, ingest_ttl
result = VinculumEngine().score(object)
```

## Narrow compatibility shim

`vinculum.compat_v04` provides `Hypothesis`, `Constraint`, and `LegacyV04Adapter` to help move v0.4-style inputs into the new measurement model. It does not recreate v0.4 governance behavior.

## Conceptual mapping

v0.4 `probability` → one possible P driver, not the whole P score.

v0.4 `Constraint` → a deterministic signal that should be represented in content or a custom scoring profile.

v0.4 `BOUNDED_ACCEPTED/REJECTED` → removed. v0.5 returns a continuous P/D position, tension, and usable value.
