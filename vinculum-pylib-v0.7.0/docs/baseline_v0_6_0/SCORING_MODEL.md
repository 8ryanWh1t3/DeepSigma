# Scoring model — VINCULUM 0.6.0

## Do not collapse five different questions

1. **Comparability:** are these representations legitimately describing the same quantity under the selected contract?
2. **Discrepancy:** what exactly differs in their values or admissible ranges?
3. **Support:** what supports the interpretation, observation and proposed alignment?
4. **Coverage:** what was actually represented, checked, compared and supported?
5. **Status:** aligned, partial, conflicting, unresolved or not comparable?

## P/D is a descriptor, not a collision detector

At every order, on either L or M, `PDProfile` may contain P and D independently in [0,1]. Neither side gets a baseline solely from its L/M label. Missing channels stay missing. P+D need not equal 1.

When both channels are known and P+D>0:

```text
position = (D-P)/(D+P)
balance  = 1-abs(position)
```

This balance describes representation characteristics only. Identical balance can accompany “13 versus 13” or “13 versus 12”; therefore balance is not contradiction. No `position` or `balance` is invented when P+D=0 or a channel is unknown.

## Exact numeric comparison

Inputs are finite decimal/rational values. Decimal strings are converted to exact rational numbers. Registered affine units are normalized exactly. The original quantities and units remain in the result; signed deltas are supplied in base units and, where defined, in the left unit.

Let E be the expected admissible set and O the observed admissible set, after legitimate alignment and unit conversion:

```text
O is contained in E             -> ALIGNED
O and E are disjoint             -> CONFLICT
O overlaps E but is not contained -> PARTIAL
```

This is directional constraint evaluation. A point and an interval are not the same thing. A source interval narrowed by a generated summary is checked separately by the codec layer, even when the new point satisfies the original broad constraint.

Raw collision score:

```text
ALIGNED           -> 0
CONFLICT          -> 100
PARTIAL           -> None
UNRESOLVED        -> None
NOT_COMPARABLE    -> None
UNPAIRED          -> no PairResult
```

A categorical score is accompanied by exact delta/boundary gap and optional normalized magnitude. `PairSpec.distance_scale` must be explicitly supplied in the left unit before a magnitude is normalized. There is no universal domain-independent scale.

An open threshold matters: “greater than 50%” compared with exactly 50% is a conflict even though the numerical distance to the boundary is zero.

## Support is separate

Each representation has a declared list of `SupportFactor` objects. Missing factors are visible. A strength is returned only when every declared factor is known and the profile is nonempty. Within each side the default strength is the minimum known coefficient, not a product of arbitrarily many correlated quantities.

Default pair-level support:

```text
joint_support = minimum(left_strength, right_strength, alignment_support,
                        every explicitly declared higher-order hinge strength)
```

If one of these is unknown, joint support is unknown. Missing declared dependence also leaves support unknown. No factors are assumed to equal 1 merely because the payload contains a number or a valid Turtle literal.

The supported collision indicator is:

```text
supported_collision_score = raw_collision_score * joint_support
```

It is unavailable when either input is unavailable. It is a **heuristic support-weighted indicator**, not probability of truth, an operational risk estimate or permission to act.

A product model is available only when `HingePolicy(support_aggregation='product', product_basis=...)` is explicitly selected. The basis is included in the report. Multiplying scores does not establish independence or probabilistic calibration. Within each representation, factors still use the bottleneck model.

## Missing or weak support cannot turn a conflict into agreement

For the same 13-versus-12 pair, with a canonical language mapping and explicitly fixed pair alignment:

| Numeric defense | Raw delta | Raw collision | Supported indication | Status |
|---:|---:|---:|---:|---|
| .99 | -1 | 100 | 99 | CONFLICT |
| .42 | -1 | 100 | 42 | CONFLICT |
| 0 | -1 | 100 | 0 | CONFLICT |
| unknown | -1 | 100 | unknown | CONFLICT |

The record remains 12 in every case. A low supported indication is not low risk, safety, resolution or evidence that the words are correct.

## Independence and calibration

Common source roots and derivation links produce explicit warnings. The system never turns duplicate displays into independent corroboration. Group rollups count pairs, not independent experiments, and retain the maximum conflict so an average cannot conceal it.

The optional `beta_calibration` helper uses an explicitly stated beta-binomial model for exchangeable Bernoulli outcomes. It reports sample count and prior/posterior parameters; zero trials produces a prior, not observed calibration. It does not calibrate arbitrary classifier confidence or transfer calibration between populations.

## Coverage

- Alignment metadata coverage: known required checks / applicable required checks. Known failures count as known metadata, not successful alignment.
- Representation support coverage: known factors / declared factors.
- Resolved pair coverage: ALIGNED or CONFLICT pairs / selected pairs. PARTIAL remains unresolved at the numeric level.
- Codec material coverage: selected source/target material nodes linked to pairs, not every possible meaning in source documents.
- Matrix evaluated-slot count: where pairs exist; it is not evidence completeness.

## Historical API

`VinculumEngine.score()` retains v0.5.2's prior heuristics, baselines and `Sigma_V` fields for compatibility. New pairwise evaluations do not use that object's `usable_value`, `tension_balance` or inferred confidence defaults. See SEMANTIC_DELTA.md.
