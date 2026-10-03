# Second-Order Defense — VINCULUM v0.5.2

## Purpose

VINCULUM is for **when words and numbers collide**. v0.5.2 adds a second-order state on each side so the system does not treat either language or numbers as uniformly deterministic.

## Language side: P → D

A phrase can be determinized into a numeric expectation, but the mapping itself has strength:

```text
S_L = semantic determinization strength ∈ [0,1]
```

Examples:

```text
"baker's dozen"  -> count = 13      S_L = 1.00
"airspace clear" -> threat_count=0  S_L = domain-defined, e.g. 0.95
```

Lower `S_L` means the words do not defend the inferred numeric expectation as strongly.

## Math / record side: D ← P

A numeric observation can be explicit while the process producing it remains uncertain.

```text
D_raw       = first-order deterministic structure
R_D         = deterministic defense strength ∈ [0,1]
U_D         = probabilistic contamination = 1 - R_D
D_effective = D_raw * R_D
```

Examples of `U_D`:

- sensor confidence below 1
- measurement uncertainty
- tolerance / error margin
- approximate equality
- estimated or model-derived values
- stochastic/distributional quantities

**Important:** `U_D` is a second-order modifier of deterministic strength. For a structured sensor record it does not automatically rewrite the record value or inject the same uncertainty into first-order `P` a second time.

## Collision

For a safely paired semantic expectation and numeric observation:

```text
C_raw = disagreement_basis * pair_alignment
C_V   = C_raw * S_L * R_D
```

For exact equality, a mismatch uses `disagreement_basis = 1`.

This separates three different questions:

1. **Do the words and number disagree?**
2. **How strongly do the words imply that number?** (`S_L`)
3. **How strongly can the observed number defend determinism?** (`R_D`)

The resulting `C_V` is the second-order collision strength.

## Why this matters

The same words and the same observed value can have different VINCULUM collision strength:

```text
WORDS:   "Airspace clear" -> expected count = 0, S_L=.95
NUMBER:  active tracks = 1

Sensor A: R_D=.99 -> strong defended contradiction
Sensor B: R_D=.42 -> weakly defended contradiction
```

The observed `1` remains `1` in both cases. What changes is how strongly that number can defend deterministic state.

## Output fields

`VinculumResult` exposes:

```text
semantic_determinization_strength   # S_L
deterministic_defense_strength      # R_D
probabilistic_contamination         # U_D
raw_deterministic_strength          # D_raw
defended_deterministic_strength     # D_effective
collision_strength                  # alias of semantic_record_tension
collision_coverage                  # alias of comparison_coverage
collision_status
primary_collision
```

Serialized results include both `second_order` and `collision_model` blocks.
