# VINCULUM v0.5.2 Architecture

## Scope lock

> **VINCULUM is for when words and numbers collide.**

It is a measurement engine, not an authority or truth-adjudication system.

## Pipeline

```text
INGEST
  ↓
DECOMPOSE
  ↓
WORDS → semantic numeric expectation
  ↓                       ↘
S_L                        VINCULUM COLLISION
                          ↗
NUMBERS → observed state
  ↓
D_raw → R_D / U_D → D_effective
  ↓
DERIVE ΣV + collision tension
  ↓
AGGREGATE
  ↓
EXPLAIN
```

## First order

### Language: P→D

Natural language starts interpretation-heavy. Explicit `MeaningRule` entries convert selected phrases into machine-comparable expectations.

### Math: D←P

Numeric records and formal expressions supply deterministic structure.

## Second order

### Language strength

```text
S_L = semantic_determinization_strength
```

This controls how strongly the phrase-to-number mapping is asserted by the active semantic registry.

### Math defense

```text
D_raw = first-order determinism
U_D   = probabilistic contamination
R_D   = 1-U_D
D_effective = D_raw * R_D
```

Uncertainty therefore does not erase the number. It reduces the number's ability to defend deterministic state.

## Stable Sigma vector

The original contract remains:

```text
ΣV = {P, D, V, τ, Coverage}
```

The `D` used for math-side third-state derivation is defended/effective determinism. The unmodified `D_raw` is retained in the `second_order` output.

## Reconciliation

```text
semantic expectation
      ↕
conservative pairing
      ↕
numeric observation
      ↓
raw contradiction
      ↓ × S_L × R_D
second-order effective collision
```

## Recursive scale

The same engine can surface collisions at:

```text
claim → episode
a clause/paragraph → document → corpus
row → dataset
RDF triple → TTL graph
```

## Boundaries

VINCULUM does not provide:

- command authority
- legal/policy approval
- cryptographic authorization
- factual truth adjudication
- causal inference
- automated action

The next operational layer may monitor streams and discover candidate word-number pairs, but the v0.5.2 core remains the scoring/reconciliation engine.

## Separation invariant

The second-order math variable is not a disguised duplicate of first-order P.

```text
first-order P  = probabilistic character of the expression/object
U_D            = uncertainty in the numeric side's ability to defend D
```

For structured records, `U_D` reduces `D_effective` without automatically raising first-order P. Pair discovery/alignment also remains outside collision strength; the core consumes pairing confidence rather than inventing it.
