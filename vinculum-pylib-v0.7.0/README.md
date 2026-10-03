# VINCULUM pyLib v0.7.0
## Input -> Runtime -> Output Integration

**When words and numbers collide.**

VINCULUM is a representation-evaluation library. Language and mathematics can each contain probabilistic and deterministic elements at any examination order. A hinge exists **only for a selected pair**; it is not a third source of truth. The library preserves comparability, discrepancy, support, uncertainty, coverage, and status as separate outputs.

This release implements the six attached architecture graphics as a bounded **INPUT -> RUNTIME -> OUTPUT** reference pipeline while preserving the v0.6.0 cross-order engine. The `v2.0` labels appearing in concept graphics remain design labels; the delivered Python package version is **0.7.0**.

## Scope lock

VINCULUM does four things:

1. **Represent** language and mathematical/numeric material without assuming either side is inherently probabilistic or deterministic.
2. **Pair** only material that an explicit/manual/guided/named policy says should be compared.
3. **Evaluate** pair-owned hinges across same-order or cross-order relationships.
4. **Report** what aligns, conflicts, remains unresolved, is only partially compatible, or is not comparable.

It does **not** adjudicate physical truth, establish authority, certify safety, or automatically execute a command action.

## What v0.7.0 adds over v0.6.0

### INPUT

- Bounded loaders for TXT/Markdown, JSON/JSONL, CSV, and native scenario data.
- Optional adapters for YAML, PDF text layers, DOCX body text/tables, XLSX, and Parquet when their host dependencies are installed.
- Explicit `FieldMapping` from source fields into typed `Representation` objects.
- `OntologyRegistry` for declared entity/concept aliases and optional RDF/SKOS-backed normalization.
- `EvidenceRegistry` with SHA-256 content identity and explicit ancestry.
- Declarative manual, guided, or named-policy pairing configuration.

### RUNTIME

```text
INPUT
  -> INGEST
  -> REPRESENT
  -> PAIR
  -> HINGE EVALUATE
  -> AGGREGATE
  -> OUTPUT
```

- `VinculumPipeline` orchestrates the complete replayable job.
- `PairPlanner` proposes or selects candidate `L_i <-> M_j` pairs without using numeric agreement as matching evidence.
- `HingeEvaluator` remains the canonical pair evaluator from v0.6.0.
- Higher-order diagnostics remain separate from first-order discrepancy; a product-style diagnostic must be explicitly declared.
- `interval_calculate()` provides bounded scalar interval arithmetic for normalized numeric expressions without `eval`, function calls, attributes, or indexing.
- `CodecEvaluator` continues to check declared source/target preservation, including scope loss, uncertainty loss, changed values, omissions, and unsupported additions.
- `RunArchive` offers an optional local SQLite replay archive; it is not an authority store or root of trust.

### OUTPUT

- Pair states: **ALIGNED, PARTIAL, CONFLICT, UNRESOLVED, NOT_COMPARABLE**.
- Sparse cross-order matrix and pair-level findings.
- JSON, CSV, Markdown, Turtle, and offline HTML export.
- Optional PDF and host XLSX exports.
- Optional authenticated FastAPI facade for bounded inline text/JSON/CSV evaluation.
- Review findings and evidence lineage for downstream human/application decision support.
- **Automatic operational actions: 0.**

## The five-order default view

The five rows are an examination scaffold, not five mandatory certainty levels:

| Order | Language example | Mathematics example |
|---|---|---|
| 1 | Content / assertion | Value / measurement |
| 2 | Qualification | Uncertainty / tolerance |
| 3 | Support | Model / method |
| 4 | Context / scope / time | Applicability / scope / freshness |
| 5 | Dependence / agreement | Dependence / agreement |

Any selected `L_i` may pair with any selected `M_j`. The 5x5 display therefore describes **25 possible order positions**, not 25 automatic comparisons. Multiple object pairs may occupy one position, and most positions may remain empty.

## Hinge contract

A selected pair is checked for relevant dimensions such as:

- same entity / object,
- same concept / property,
- compatible units,
- compatible population and denominator,
- compatible granularity,
- compatible scope and time,
- method / evidence alignment where declared.

A known mismatch in subject/type is **NOT_COMPARABLE**, not `CONFLICT`. Missing required information is **UNRESOLVED**, not false, zero, or low risk. An unpaired node has no collision score.

## Install

```bash
python -m pip install dist/vinculum_pylib-0.7.0-py3-none-any.whl
```

Python >=3.10 is declared. Core runtime dependency: `rdflib>=7.0`. Optional extras are declared for tests, documents, YAML config, API, PDF, and Parquet support.

## Canonical pipeline example

```python
from vinculum import VinculumPipeline

result = VinculumPipeline().run_file("examples/cross_order_pipeline.json")
print(result.report.summary)
print(result.stage_trace)
result.export("out", formats=("json", "html", "csv", "md", "ttl"))
```

The delivered synthetic codec-limit scenario retains the direct v0.6.0 pair outcomes while adding source identity, extraction trace, ontology normalization, evidence checks, pairing audit, higher-order diagnostics, review findings, and replay identity.

## CLI

```bash
vinculum-pipeline --version
vinculum-pipeline capabilities
vinculum-pipeline run examples/cross_order_pipeline.json --summary
vinculum-pipeline run examples/bakery_pipeline.json --out-dir out --formats json,html,csv,md,ttl
```

Legacy `vinculum` and `vinculum-lattice` commands are preserved.

## Optional HTTP adapter

```python
from vinculum.api import create_app
app = create_app(token="deployment-owned-token-at-least-16")
```

The reference API accepts only bounded inline text/JSON/CSV jobs, does not fetch remote sources, and rejects job-supplied executable regex lexicons. Production IAM, mission authorization, and operational connectors are outside this package.

## Delivered examples

- `examples/bakery_pipeline.json` - semantic number versus receipt quantity.
- `examples/coverage_pipeline.json` - cross-order language-to-scope comparison.
- `examples/cross_order_pipeline.json` - full five-order codec stress case.
- `demo_output/report.html` - offline review surface.
- `demo_output/VINCULUM_Pipeline.xlsx` - optional spreadsheet evidence surface.
- `demo_output/REPORT.pdf` - optional executive report.

## Compatibility

The v0.5.2 object-scoring API and v0.6.0 cross-order primitives remain available. v0.7.0 adds orchestration instead of silently retuning `core`, `hinge`, `math`, `lang`, `codec`, `monitor`, `rdf`, or `serialization`.

See `SEMANTIC_DELTA.md` for measured source differences and `MIGRATION_V0_6_TO_V0_7.md` for the adoption path.

## Attached-graphic boundary

The six supplied diagrams are treated as design requirements, not evidence that every pictured platform connector or philosophical claim is executable. In particular:

- the **origin / God / Big Bang / retreat** framing is retained only as attributed `NarrativeContext` and never enters a score;
- Foundry, Vantage, OnBase, Lattice, A365 and similar names in the graphics are downstream integration targets, not implemented live connectors;
- the library evaluates representations and relationships between them, not reality itself.

See `GRAPHIC_TRACEABILITY.md`, `INPUT_RUNTIME_OUTPUT.md`, `ARCHITECTURE.md`, `SCORING_MODEL.md`, `HINGE_CONTRACT.md`, `CODEC.md`, `MONITOR.md`, `SECURITY.md`, and `VALIDATION.md`.
