# Migration: 0.6.0 → 0.7.0

## Existing callers

`PairGraph`, `CrossOrderEngine`, `HingeEvaluator`, the native scenario schema, `vinculum-lattice` and legacy `VinculumEngine` still work. All original test files are unchanged. Original comparison kernels were not retuned. New behavior enters through `VinculumPipeline` and its adapters.

## Wrap an existing scenario

```python
from vinculum import VinculumPipeline
from vinculum.serialization import load_scenario

scenario = load_scenario('examples/cross_order_scenario.json')
job = {'schema':'vinculum.pipeline.job/1', 'scenario':scenario.to_dict(),
       'pairing':{'mode':'manual'}}
result = VinculumPipeline().run(job)
```

Supply `evidence` entries for declared source IDs when their registration/ancestry should be checked. `require_registered_sources=True` makes missing registered evidence block legitimate comparison. In the new pipeline, missing registered ancestry also withholds a support-weighted value even when raw comparison is permitted. Direct v0.6 APIs retain their own behavior.

## Add source extraction

Use `sources` with exactly one of `data` or local `path`, plus a `FieldMapping`. Specify entity, concept, unit and full scope; do not rely on matching column names alone. Language mappings may use the default exact phrase lexicon or a trusted local `lexicon` entry.

Ontology canonicalization follows lexical extraction. Therefore a constrained language rule/mapping should use its canonical concept ID; ontology alias normalization is not an arbitrary-prose meaning resolver.

## Enable pairing deliberately

`manual` is default. `guided` accepts explicit endpoint choices. `auto` requires `policy_id` and `basis`, and selects only globally unique metadata-complete one-to-one pairs. Failing or ambiguous metadata is not resolved by choosing the closest number.

Auto mode does not assign alignment probability. A supported score may remain unknown until you explicitly supply justified alignment support. This is expected, not an error.

## Higher-order products

The graphics' product model can be explored with:

```json
{"higher_order":{"aggregation":"product","joint_aggregation":"product",
 "product_basis":"Declared sensitivity index for this application; not probability."}}
```

This changes the separate diagnostic block, not base raw discrepancy. Repeated dependency groups are bottlenecked. Registered shared ancestry caps requested pair-support products. Keep minimum aggregation for baseline interpretation unless a defensible application model justifies otherwise.

## Replay and file paths

Exported JOB.json is the complete declarative recipe, with content hashes attached. Inline jobs are self-contained. File-backed jobs still require the original input files beneath the same authorized job root; files are not silently copied or paths rewritten. `scenario.ttl` contains the typed graph and core policy, not all pipeline ingestion/evidence plugin configuration. Use JOB.json for full pipeline replay.

## Naming

Use the actual package version 0.7.0. The attached images' 2.0 labels are concept labels, not a migration from a real 2.0 package.
