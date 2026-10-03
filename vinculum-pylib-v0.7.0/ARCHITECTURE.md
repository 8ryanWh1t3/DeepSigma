# Architecture - VINCULUM pyLib v0.7.0
## Input -> Runtime -> Output over the v0.6.0 cross-order hinge

## 1. Architectural invariant

```text
Representations carry orders.
Pairs create hinges.
Hinges evaluate comparability and discrepancy.
VINCULUM reports the relationship.
```

Language is not probabilistic by definition and mathematics is not deterministic by definition. Either side may contain both P and D characteristics at every order. No hinge or collision exists before a pair is selected.

## 2. INPUT plane

The input plane is deliberately declarative and bounded.

### Source material

- language: text, documents, claims, labels, reports, policies, model/LLM output;
- mathematics/numeric: measurements, calculations, intervals, models, time series, sensor records, statistics;
- structured context: JSON/JSONL, CSV, native Turtle/RDF, and explicitly mapped records;
- optional host formats: PDF text layer, DOCX body text/tables, XLSX, YAML, Parquet.

File loading never claims unrestricted semantic understanding. PDF is text-layer extraction, not OCR/layout cognition. DOCX body extraction does not interpret images, footnotes, comments, or tracked changes. XLSX/Parquet are optional host adapters.

### Context and mappings

`FieldMapping` specifies how a record becomes a representation. `OntologyRegistry` may normalize declared entity/concept aliases. `EvidenceRegistry` records source identity and ancestry. `PairingPlan` describes how candidate pairs are selected.

## 3. RUNTIME plane

### Stage 1 - INGEST

`vinculum.io` loads bounded local or inline inputs, computes source identity, and retains locators/warnings.

### Stage 2 - REPRESENT

`vinculum.represent` creates order-aware L/M `Representation` objects. Each object preserves its own:

- entity and concept,
- numeric set/interval if one exists,
- unit,
- scope / population / denominator / granularity / time,
- P/D profile,
- support factors,
- source and dependency IDs,
- original text / locator.

Unknown numeric meaning stays unknown; it is never silently converted to zero.

### Stage 3 - PAIR

`PairPlanner` builds a candidate relation over metadata-complete language and mathematics objects. Numeric agreement is explicitly excluded from pair discovery so the system cannot select only pairs that already agree.

Modes:

- `manual`: caller supplies exact endpoints;
- `guided`: candidates are produced, caller selects explicit endpoints;
- `auto`: only a named, attributed, unique one-to-one exact-metadata policy may auto-select.

Many-to-many ambiguity remains deferred.

### Stage 4 - HINGE EVALUATION

The canonical v0.6.0 `HingeEvaluator` evaluates each selected pair. Required checks distinguish:

- comparable and aligned,
- comparable but partially overlapping,
- comparable and conflicting,
- unresolved because information is missing,
- not comparable because identity/type/dimension constraints fail.

Discrepancy, support, coverage, and status remain separate. A weak source does not rewrite a recorded number or erase a known delta.

### Stage 5 - HIGHER-ORDER / CODEC / AGGREGATION

- `higher_order` evaluates declared support structure without silently changing raw pair status.
- `CodecEvaluator` checks whether material representations survive a declared transformation.
- `ObjectGroup` rolls selected distinct pair IDs through claim / episode / document / graph / corpus structures without double-counting overlapping child groups.

### Stage 6 - OUTPUT

`findings`, `report`, `exports`, and `pipeline_excel` project the same evaluated state into review artifacts. Output never performs an operational command action.

## 4. Pair-owned hinge model

A pair may connect any order:

```text
H_ij^(k)
```

where `i` is the language order, `j` is the mathematics order, and `k` is a pair-local hinge examination order. `i` need not equal `j`.

The default order legend is:

| Order | L-side question | M-side question |
|---|---|---|
| 1 | What is asserted? | What value is measured/calculated? |
| 2 | What qualifiers constrain the claim? | What uncertainty/tolerance accompanies the value? |
| 3 | What supports the interpretation? | What model/method supports the number? |
| 4 | When/where does it apply? | Is the number applicable/fresh in that scope? |
| 5 | Is it independent/derived? | Are numerical sources independent/derived? |

These are default examination roles, not universal epistemic laws. Positive orders beyond five are supported.

## 5. Exact and uncertain mathematics

`NumericRange` stores admissible sets, not probability distributions. `interval_calculate()` propagates finite closed intervals through bounded `+ - * /` expressions and preserves enclosures. It intentionally does not infer correlation or cancel repeated-variable uncertainty.

## 6. Evidence and ontology

`EvidenceSource` SHA-256 establishes content identity, not truth. Evidence ancestry is explicit. Missing registered ancestry can withhold supported scores while leaving raw discrepancy visible.

Ontology normalization can resolve declared aliases, but ambiguous or undeclared meaning remains unresolved. The ontology does not grant authority.

## 7. API and persistence

The optional FastAPI facade is stateless evaluation only, with bounded request size and optional bearer-token protection. It forbids path-based source loading and job-owned regex lexicons.

`RunArchive` is an optional SQLite content archive with payload digest checking. It is not an append-only enterprise ledger, authoritative repository, or trust anchor.

## 8. Narrative context boundary

The supplied big-picture diagrams include an origin / God -> Big Bang -> nature -> cellular/divisional reality and a retreat path toward presence before language/math. VINCULUM stores that framing only as attributed `NarrativeContext` for presentation. It does not score God, spirituality, cosmology, nature, presence, or retreat, and does not encode a theological or causal claim as a numeric model.

## 9. Module map

| Module | Responsibility |
|---|---|
| `core` | v0.6.0 typed representation/pair/result structures |
| `io` | bounded source loading |
| `represent` | explicit field-to-representation mapping |
| `ontology` | declared entity/concept normalization |
| `evidence` | source identity, ancestry, evidence hinge checks |
| `pairing` | batch-wide candidate planning and explicit-policy selection |
| `hinge` | canonical pair compatibility and discrepancy evaluation |
| `higher_order` | separate higher-order support diagnostics |
| `symbolic` | bounded exact/interval scalar arithmetic |
| `codec` | source/target representation preservation checks |
| `matrix` | sparse cross-order pair graph and aggregation |
| `pipeline` | INPUT -> RUNTIME -> OUTPUT orchestration |
| `findings` | review queue projection |
| `exports` | JSON/CSV/MD/TTL/HTML/PDF output adapters |
| `pipeline_excel` | optional host XLSX evidence surface |
| `api` | optional bounded HTTP evaluation facade |
| `store` | optional local replay archive |
| `context` | non-scored attributed narrative context |

## 10. Boundary

VINCULUM is a reference measurement/evaluation library. It does not prove physical truth, authorize policy, identify hostile targets, perform sensor fusion, replace safety analysis, or apply command decisions. Downstream systems may consume results only under their own authority, validation, and mission controls.
