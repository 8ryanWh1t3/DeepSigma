# Validation — VINCULUM pyLib v0.5.0

## Release target

**VINCULUM pyLib v0.5.0 — P↔D Tension Engine**

The acceptance target is the scope-reset kernel:

`INGEST → DECOMPOSE → SCORE P → SCORE D → DERIVE V/τ → AGGREGATE → EXPLAIN`

## Source validation

- Python compileall: **PASS**
- Unit tests from source: **49 / 49 PASS**
- Failures: **0**
- Errors: **0**

Coverage includes formulas, normalization, usable-value damping, intensity-aware tension, language P→D, math D←P, recursive aggregation, object weights, episodes, datasets, TTL/RDF graphs, malformed Turtle fallback, CLI behavior, long literal safety, custom thresholds, and the narrow v0.4 migration shim.

## Built-wheel validation

- Wheel built offline with local build tooling: **PASS**
- Wheel installed into a fresh virtual environment: **PASS**
- Unit tests against installed wheel: **49 / 49 PASS**
- Failures: **0**
- Errors: **0**

The test environment supplied the declared runtime dependency `rdflib>=7.0` from the host Python installation; VINCULUM itself was imported from the installed wheel.

## Installed CLI smoke tests

`vinculum score examples/sample.ttl --summary`: **PASS**  
`vinculum score examples/document.txt --summary`: **PASS**  
`vinculum score-json examples/episode.json --type episode --summary`: **PASS**

`TTL: score=93.52, tension=0.064, usable=93.52, state=DETERMINISTIC_DOMINANT
DOCUMENT: score=50.63, tension=0.504, usable=50.63, state=BOUNDARY_TENSION
EPISODE: score=59.12, tension=0.353, usable=59.12, state=BOUNDARY_TENSION`

## Wheel integrity

- Wheel: `vinculum_pylib-0.5.0-py3-none-any.whl`
- SHA-256: `40f2c42d052145fc0f853db46ff3edbc994fcadf6a144098fb6556e484f06c57`

## Scope assertions

- Core invokes no LLM: **PASS**
- Core contains no root-of-trust / authorization / CERPA APPLY logic: **PASS**
- P and D remain separately observable: **PASS**
- Third state includes `V`, `τ`, coverage, tension index, and usable value: **PASS**
- TTL scores recursively from RDF triples plus graph-level parse structure: **PASS**
- v0.4 governance behavior is not recreated in the core: **PASS**

## Important interpretation boundary

VINCULUM is **not a truth score**. The tests intentionally include a deterministic-but-factually-wrong sentence to ensure deterministic form is not confused with factual correctness.
