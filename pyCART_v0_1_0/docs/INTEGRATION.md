# Host integration — explicit boundaries

## Inspected baseline

The supplied `DeepSigma-main (18).zip` identifies the base package as `deepsigma` 2.1.2, source root
`src/core`, Python >=3.10, with the core package finder matching `core*`. This is a provided snapshot,
not verification of the latest live GitHub branch. Its hashes are in `verification/baseline.json`.

The add-on uses its own import root, `deepsigma_cartography`, and does not overwrite `core` or
`vinculum`. To expose `core.cartography`, install this wheel and copy the provided shim directory
into the host repository's `src/core/cartography/`. Declare `deepsigma-cartography==0.1.0` as a host
dependency. Preserve any existing cartography implementation instead of overwriting it. No source
changes were pushed to GitHub and no user repository was modified by this build.

## Native Memory Graph

```python
from core.memory_graph import MemoryGraph
from deepsigma_cartography import from_memory_graph

mg = MemoryGraph()
# Populate through the existing host APIs.
atlas = from_memory_graph(mg, atlas_id="atlas:mission-01", title="Mission meaning map")
```

The adapter reads the actual `to_json()` export: nodes with node_id/kind/label/timestamp/properties,
and edges with source_id/target_id/kind/label/properties. It does not require private collection
access. Native IDs are retained. Duplicate native edges receive deterministic occurrence IDs.
Original source records are preserved. Native confidence is not silently rescaled from a guessed
0–100 scale. A source timestamp is retained but is not guessed to be a validity bound.

Known native `claim_depends_on`, `claim_supports`, `claim_evidence`, and `claim_source` relations get
their documented orientation. Native `claim_contradicts` remains an explicitly recorded contradiction.
Other native kinds remain visible with no invented propagation semantics. Source-labeled native
evidence nodes become an evidence reference, marked `verification: not_performed`.

## CERPA

```python
from core.cerpa.models import Review, Patch
from deepsigma_cartography import assess, cerpa_review, patch_proposals

view = atlas.view(as_of="2026-10-03T12:00:00Z")
assessment = assess(view)
# The two IDs must already exist with the indicated kinds in this view.
draft = cerpa_review(view, assessment, claim_id="claim:01", event_id="event:01", domain="mission")
review = Review(**draft)
patches = [Patch(**p) for p in patch_proposals(assessment, review_id=review.id, domain="mission")]
```

These constructor contracts were tested against the provided snapshot. They do not exercise a
production authority service. The host must honor `metadata.status=PROPOSED`. A single static map
is not a temporal drift detector: Review.drift_detected is False and metadata.drift_status is
`not_evaluated`. The draft concerns structural checks across the entire map, not an adjudication of
the claim's truth against the event. Keep it a review task until the host review process resolves it.

Cartography does not call `ApplyResult`, publish a policy, sign an approval, enroll a root, load a
private key, or change the authoritative corpus. No new Policy Fence is embedded here.

## VINCULUM pyLib 0.7.0

Retrieved migration notes preserve PairGraph/CrossOrderEngine/HingeEvaluator/PairingMonitor/
CodecEvaluator/legacy VinculumEngine, and identify VinculumPipeline for file orchestration. They
do not define a compatible native Cartography hook. This release exports
`deepsigma.cartography.vinculum-projection/1` as a **proposed** read-only envelope, preserving original
IDs, attributes, context, evidence, and view identity. A host adapter is still needed to bind it to
the real VINCULUM renderer. No claim of native UI integration or end-to-end pipeline testing is made.

MERIDIAN's current executable interface was not located. Reversible grouping in this module is not
represented as a verified MERIDIAN integration or implementation of unspecified 4D equations.

## Operational adoption

Use one authorized, bounded mission data set. Define predicate meanings and coverage expectations.
Generate the map and findings; review omissions and false positives. Reuse native authority services
for any change. Require integration regression tests against the actual deployment branch before
promoting from this add-on's initial release to operational use.
