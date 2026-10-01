# Scoring Model — v0.5.2

## 1. First-order P/D model

VINCULUM retains the v0.5.x base channels:

- Language baseline: P=0.45, D=0.15
- Math baseline: P=0.05, D=0.65 when formal structure exists
- Structured data baseline: P=0.15, D=0.45
- TTL baseline: P=0.05, D=0.75 for valid parse

The stable vector remains:

```text
p = P/(P+D)
d = D/(P+D)
V = d-p
V_score = 50*(V+1)
τ = 1-|V|
intensity = (P+D)/2
tension_index = τ*intensity*Coverage
usable_value = 50*(1 + V*Coverage)
```

## 2. Language second order — semantic determinization strength

A `MeaningRule` resolves a recognized phrase into a machine-comparable expectation.

```text
"baker's dozen" → count == 13
```

Each meaning has:

```text
S_L = semantic_determinization_strength ∈ [0,1]
```

`S_L=1` means the phrase-to-number mapping is treated as canonical by the active registry. Lower values preserve semantic ambiguity.

## 3. Math second order — deterministic defense

The numeric side now separates first-order structure from second-order reliability:

```text
D_raw = deterministic structure before uncertainty defense
U_D   = probabilistic contamination ∈ [0,1]
R_D   = 1 - U_D
D_effective = D_raw * R_D
```

### Explicit reliability

When math or a record states confidence/reliability explicitly, that value becomes `R_D`.

Examples:

```text
reliability 55%  → R_D=.55, U_D=.45
80% confidence  → R_D=.80, U_D=.20
```

### Derived reliability

If no explicit value exists, math uncertainty signals produce `U_D`:

```text
U_D = 1 - exp(-E_P / k)
R_D = 1 - U_D
```

where `E_P` is accumulated math-side probabilistic evidence and `k` is `math_uncertainty_scale` (default 3.0).

Approximation, ± uncertainty, probability/confidence markers, stochastic constructs, and estimation language contribute to `E_P`.

## 4. Structured record defense

Numeric records may carry local quality fields:

```text
confidence
reliability
sensor_confidence
measurement_confidence
record_confidence
deterministic_defense
certainty
quality_score
```

The weakest valid local value is used when more than one is present. This is deliberately conservative.

If no quality field is present:

```text
R_D = 1.0
```

## 5. Semantic-to-record comparison

For a paired semantic fact and record fact:

```text
C_raw = disagreement_basis * alignment_score
C_effective = C_raw * S_L * R_D
```

For exact equality mismatch:

```text
disagreement_basis = 1.0
```

For inequality/bound cases, normalized delta contributes to disagreement magnitude.

The output preserves both:

- `raw_conflict_strength` — what the contradiction would be if both sides were maximally strong
- `conflict_strength` — second-order effective contradiction after `S_L` and `R_D`

## 6. Object-level collision

```text
semantic_record_tension = mean(conflict_strength_i)
comparison_coverage = safely_paired_semantic_facts / comparable_semantic_facts
```

The legacy conflict-adjusted usability remains:

```text
reconciled_usable_value
  = usable_value * (1 - semantic_record_tension * comparison_coverage)
```

It is not a truth score.

## 7. Interpretation

Two identical numeric mismatches can have different significance:

```text
Words imply 0, record says 1, R_D=.99 → strong collision
Words imply 0, record says 1, R_D=.42 → weaker deterministic defense
```

The second case does not make the words correct. It means the number is less capable of defending deterministic reality against uncertainty.

## 8. Second-order separation

For structured numeric records, probabilistic contamination modifies deterministic defense:

```text
D_effective = D_raw * R_D
```

It is not automatically injected into first-order `P` again. This prevents double-counting the same sensor/reliability uncertainty.

Formal math uncertainty markers such as `≈`, `±`, stochastic distributions, or explicit probability language may affect both channels because they are simultaneously first-order probabilistic expressions and evidence that deterministic defense is weaker.

## 9. Collision model

For a safely paired words↔numbers comparison:

```text
C_raw = disagreement_basis * alignment_score
C_V   = C_raw * S_L * R_D
```

Serialized comparison results expose both legacy names (`raw_conflict_strength`, `conflict_strength`) and canonical collision aliases (`raw_collision_strength`, `collision_strength`).
