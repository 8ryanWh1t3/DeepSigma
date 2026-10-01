# Migration — v0.5.1 → v0.5.2

v0.5.2 is additive and preserves the v0.5.1 meaning-resolution and record-comparison APIs.

## New second-order fields

`VinculumResult` adds/exposes:

- `semantic_determinization_strength` (`S_L`)
- `deterministic_defense_strength` (`R_D`)
- `probabilistic_contamination` (`U_D = 1-R_D`)
- `raw_deterministic_strength` (`D_raw`)
- `defended_deterministic_strength` (`D_effective`)
- `collision_strength` property
- `collision_coverage` property
- `collision_status` property
- `primary_collision` property

JSON output adds `collision_model` while preserving `Sigma_V`, `second_order`, `tension_model`, and `semantic_reconciliation`.

## Record confidence

Structured numeric records may now include local second-order keys such as:

```text
sensor_confidence
measurement_confidence
record_confidence
reliability
confidence
certainty
deterministic_defense
quality_score
```

Values may be `0..1`, `0..100`, or percentage strings.

## Math uncertainty

Formal math now distinguishes `D_raw` from `D_effective`. Approximation, uncertainty, distributions, and explicit confidence can reduce deterministic defense.

## Behavioral note

For structured records, `U_D` weakens `D`; it is not automatically double-counted as additional first-order `P`. This preserves the second-order interpretation.
