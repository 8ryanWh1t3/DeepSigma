# Migration from 0.5.2 to 0.6.0

## No hidden replacement

The supplied 0.5.2 ZIP matched its previously reported SHA-256, and its 74 tests passed before extension. Original functional modules and tests are retained byte-for-byte; release metadata and package exports identify the new release separately. Exact module hashes are recorded in SEMANTIC_DELTA.json.

Existing use remains valid:

```python
from vinculum import VinculumEngine, ingest_mapping
legacy = VinculumEngine().score(ingest_mapping(payload))
```

The new architecture is explicit:

```python
from vinculum import PairGraph, CrossOrderEngine
# Add typed nodes, scopes, higher-order factors and explicit pairs.
report = CrossOrderEngine().evaluate(graph)
```

## Deliberate new semantics

| 0.5.2 path | 0.6 cross-order path |
|---|---|
| Side-specific heuristic P/D baselines | No P/D baseline inferred from L/M |
| P/D balance sometimes called tension | Balance remains a descriptor; discrepancy comes from paired values |
| Generic structured record may default to defense 1 | Missing defense stays missing |
| Alignment and support folded into collision | Raw discrepancy/status retained separately from supported indication |
| Object scoring can operate without a meaningful pair | Unpaired objects have no pair-collision score |
| Context inferred through bounded reconciliation | Required explicit identity, concept, denominator, time and units |
| Two-side coefficient model | Arbitrary examination orders per side and per pair-local hinge |
| Generic language fragments may have heuristic scores | New semantic parser full-matches explicit rules; unknown clauses retained |

Default new support aggregation is bottleneck/minimum, not the prior three-factor product. A declared product policy remains available with an explicit basis. Neither method is automatically a probability.

Do not compare old `usable_value` or old `tension_index` directly with new raw/supported collision indicators as a time series. Keep the model version and input contract alongside each result.

## Practical migration

1. Assign canonical entity and concept IDs to your existing records and phrase-derived expectations.
2. Specify the same population, denominator, scope and time window for legitimate comparisons.
3. Put uncertainty in support profiles or numeric intervals; do not overwrite observed values.
4. Represent higher-order claims as typed nodes when they themselves need comparison.
5. Select pairs or review monitor proposals; leave unsupported mappings unresolved.
6. Use `report.pairs`, `report.matrix`, `report.summary` and group rollups instead of interpreting a single scalar as truth.
7. Retain original source references and explicit extractor/registry definitions.

The graphics' “VINCULUM 2.0” label is not used as a fictional historical software release. This extension is version 0.6.0.
