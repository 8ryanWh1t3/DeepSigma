# Declared semantic delta — 0.6.0 → 0.7.0

The update adds orchestration and adapters, not a new default truth formula.

Measured comparison: **21 of 26 existing Python modules are byte-identical**. Five changed modules are `__init__.py` (version/new exports) and `excel.py`, `lattice_cli.py`, `matrix.py`, `report.py` (release-version labels only). The actual original `core.py`, `hinge.py`, `math.py`, `lang.py`, `codec.py`, `monitor.py`, `rdf.py` and `serialization.py` remain byte-identical.

Fifteen new modules implement the pipeline additions. All 14 baseline test files are byte-identical. All 189 baseline tests continue to run.

## Intentionally new behavior, pipeline path only

- Source loading and field mapping precede graph evaluation.
- Explicit ontology normalization can establish canonical IDs; ambiguous labels become unresolved.
- Exact-metadata batch pairing may select unique pairs under a named policy. Base PairGraph callers remain explicit.
- Registered-source requirements can block comparison. Missing evidence ancestry withholds supported scores; shared ancestors cap requested products at bottleneck support.
- Separate higher-order diagnostics may use a declared product; they never replace raw comparison status/delta.
- Inputs are pinned by source/configuration fingerprints and can be exported as a replay recipe.

The nine-pair synthetic fixture retains the same status, discrepancy and raw collision fields as direct baseline scenario evaluation. Additional pipeline evidence checks and fingerprints are expected to differ.

SHA-256 comparison data: SEMANTIC_DELTA.json. Hash equality is byte identity, not proof of algorithmic correctness.
