# Semantic Determinization + Second-Order Record Reconciliation

## Core problem

Words can imply numbers. Records can contain numbers. VINCULUM measures when those values collide.

```text
"baker's dozen" → 13
receipt quantity → 12
```

v0.5.2 adds a second question:

> How strongly can the record's number defend determinism?

## Semantic fact

A resolved phrase carries:

```text
dimension
operator
value
unit
S_L / confidence
concept key
```

## Record fact

A numeric record carries:

```text
dimension
operator
value
unit
R_D / confidence
U_D = 1-R_D
path / source
```

## Conservative alignment

Pairing priority remains:

1. exact concept identity
2. same local structured container
3. singleton same-dimension fallback
4. otherwise UNRESOLVED

v0.5.2 does not loosen pairing merely because a confidence value exists.

## Comparison

Each `ComparisonResult` now exposes:

```text
semantic_determinization_strength
record deterministic_defense_strength
record probabilistic_contamination
raw_conflict_strength
conflict_strength
```

Thus an exact mismatch can have:

```text
raw_conflict_strength = 1.0
effective conflict_strength = 1.0 * S_L * R_D * alignment
```

## Supported record reliability forms

Structured data accepts local fields such as:

```text
{"quantity":12, "confidence":0.90}
{"count":1, "sensor_confidence":"42%"}
{"count":1, "reliability":55}
```

Text math accepts forms such as:

```text
x = 4 with reliability 55%
x ≈ 4 ± 0.5 with 80% confidence
```

TTL/RDF supports confidence/reliability predicates on the same subject as a numeric record predicate.
