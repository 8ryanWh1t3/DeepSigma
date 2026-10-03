# Semantic delta — 0.5.2 to 0.6.0

The 9 original functional Python modules are byte-identical to the verified baseline. `__init__.py` changes only version/export wiring for the new API. All 10 original test files are byte-identical.

The new API deliberately changes scoring semantics without silently retuning legacy callers. New module names and measured SHA-256 values are recorded in `SEMANTIC_DELTA.json`.

New-path changes: either side can carry both P/D; hinges require explicit pairs; unknown support is not 1; balance is not contradiction; raw discrepancy/status survive support reduction; non-comparability is separate; the default pair support model is a documented minimum coefficient. Optional product aggregation requires a declared basis.
