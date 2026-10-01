# Changelog

## 0.5.2 — Second-Order Deterministic Defense

- Formalized `S_L` semantic determinization strength.
- Added `R_D` deterministic defense strength.
- Added `U_D = 1-R_D` probabilistic contamination.
- Added first-order `D_raw` and second-order `D_effective` outputs.
- Math-side uncertainty now weakens deterministic defense instead of only adding P pressure.
- Explicit confidence/reliability values override derived math defense.
- Structured record confidence/reliability can weaken record determinism.
- Percentage and 0..100 reliability values normalize to 0..1.
- TTL/RDF same-subject confidence/reliability can weaken numeric-record defense.
- `ComparisonResult` now preserves raw and effective conflict strength.
- `semantic_record_tension` now reflects `S_L × R_D` second-order strength.
- Added C-UAS second-order example and regression tests.
- Kept structured-record `U_D` separate from first-order P to avoid double-counting sensor uncertainty.
- Added canonical collision aliases and a serialized `collision_model` block.
- Preserved the v0.5.1 semantic reconciliation model and stable `Sigma_V` output keys.

## 0.5.1

Semantic determinization and cross-object deterministic comparison.

## 0.5.0

Scope reset to P↔D tension measurement.
