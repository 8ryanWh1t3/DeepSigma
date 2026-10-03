# Architecture — VINCULUM 0.6.0

## The trunk

```text
Represent reality in language and mathematics
    -> retain P/D, order, scope, source and uncertainty per representation
    -> propose pairs (optional monitor)
    -> select meaningful pairs
    -> evaluate pair-specific hinge checks H(L_i, M_j; k)
    -> compare numeric states where the contract permits
    -> retain discrepancy, support, coverage and outcome independently
    -> aggregate selected pairs through claims, episodes, documents and corpora
    -> export / inspect
```

The hinge is not an object that has meaningful collision data before a pair exists. It belongs to a selected relationship. Order i need not equal order j. Higher examination order does not imply greater certainty, importance or authority.

## Modules

| Module | Responsibility |
|---|---|
| `core` | Immutable typed representation, bounds, scope, support and pair/result structures |
| `lang` | Explicit full-match numeric lexicon, narrow duration grammar and document segmentation |
| `math` | Exact rational unit conversion, admissible-set comparison and an optional explicit calibration model |
| `hinge` | Mandatory compatibility checks plus attributed, higher-order hinge states and extension checks |
| `matrix` | Sparse explicit pairs, cross-order view, dependence DAG and object-group rollup |
| `monitor` | Bounded candidate-pair discovery over normalized records; no automatic evaluation or action |
| `codec` | Source/target preservation tests over declared material representations |
| `serialization` | Strict JSON scenarios, typed restoration, unknown-key rejection |
| `rdf` | Native RDF projection plus lossless payload; generic RDF requires a field map |
| `report` | JSON, Excel-ready CSV and accessible offline HTML |
| `excel` | Optional artifact_tool XLSX adapter |
| `adapters` | Trusted application plugin protocol for LLM, symbolic, numeric or graph extractors |
| `context` | Attributed, unscored philosophical origin and retreat paths |
| `lattice_cli` | New CLI; legacy CLI remains separate |

## Representations

`Representation` contains a stable local ID, L/M side, positive order, entity, concept, quantity, unit, scope, original text, P/D descriptors, support factors, source IDs and dependency IDs. Unknown quantities are `None`; they are not zero, unconstrained intervals or automatically rejected facts.

A `NumericRange` is a set of admissible values, not a probability distribution. A point is a singleton set. A lower/upper inequality uses an unbounded opposite endpoint. Explicit intervals allow overlap to be distinguished from disjointness.

`SupportFactor` has its own examination order, attributed basis, optional source and dependency group. Support questions can themselves be represented as nodes: for example, language order 2 asserting “at least 95% validation accuracy” can pair with mathematics order 3 recording a measured validation proportion. This avoids hardwiring every higher order as a multiplier.

## Pairing

A `PairSpec` binds exact representation IDs and an explicit rationale. Multiple pairs can occupy a single matrix cell, but duplicate ordered endpoint pairs are rejected. Same-side source/target pairs are allowed for codec comparison and are reported outside the L×M matrix.

A `HingeOrderState` attaches P/D and support at a chosen examination order to this pair. Built-in mandatory checks always run, even if the caller asks to inspect only one hinge order. Custom checks can add restrictions but cannot override mandatory failures.

## Aggregation

`ObjectGroup` supplies a flexible hierarchy: claim, episode, document, dataset, TTL graph, corpus or an application-defined kind. Rollups use distinct selected pair IDs whose endpoints are both within the group's transitive member set. Overlapping subgroups cannot count the same pair twice in their parent.

Counts, maximum collision, assessed-pair mean, coverage and unpaired material nodes are retained. Numeric deltas in different units are never summed. A mean over measured pairs is not represented as coverage of the full corpus.

## Context boundary

Origin and retreat paths belong in `NarrativeContext`, not `Representation`. They appear only in presentation/serialization context and do not affect the evaluation fingerprint or numerical result. The core rejects narrative objects as scoring inputs. Context is attributed to the user's philosophical/theological framing; the library does not establish cosmological or theological conclusions.

## Compatibility isolation

The old v0.5.2 engine modules and test files are preserved. Their behavior is not silently retuned. The new architecture enters through `PairGraph` and `CrossOrderEngine`. Historical docs are preserved under `docs/legacy_v0_5_2`, not presented as current specifications.
