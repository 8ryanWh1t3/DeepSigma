# INPUT -> RUNTIME -> OUTPUT contract - v0.7.0

## INPUT

The caller supplies **representations, context, and pairing intent**.

### Language inputs

Claims, reports, policies/doctrine, natural language, model/LLM outputs, metadata, RDF labels, or structured text.

### Mathematics inputs

Measurements, counts, calculations, formulas, statistical outputs, models/simulations, intervals, sensor/telemetry values, time series, or structured records.

### Supporting context

Ontology/term aliases, entity mapping, units, scope, population, denominator, time windows, evidence identity/ancestry, and pairing rules.

## RUNTIME

1. **INGEST** - parse bounded source formats, retain source hashes/locators/warnings.
2. **REPRESENT** - create typed L/M objects; normalize declared units/terms; retain P/D, order, source, scope, support, uncertainty.
3. **PAIR** - create/select meaningful cross-order candidates. Numeric agreement is never pair-selection evidence.
4. **EVALUATE** - run pair-owned hinge checks and numeric-set comparison.
5. **AGGREGATE / CODEC / HIGHER ORDER** - preserve distinct-pair rollups, transformation checks, and separate support diagnostics.
6. **OUTPUT** - findings, evidence, replay identity, reports, matrix views, exports.

## OUTPUT

### Pair states

- **ALIGNED** - comparable and within declared admissible bounds.
- **PARTIAL** - comparable ranges overlap, so both agreement and disagreement remain possible.
- **CONFLICT** - comparable and inconsistent.
- **UNRESOLVED** - required information is missing.
- **NOT_COMPARABLE** - the selected objects do not form a valid semantic/numeric comparison.

### Artifacts

Pair-level results, sparse order matrix, review findings, evidence lineage, codec report, object-group rollups, JSON/CSV/MD/TTL/HTML and optional PDF/XLSX.

## Non-negotiable boundary

The runtime provides **decision support**, not a command decision. It emits no automatic operational action, no authority grant, and no truth adjudication.
