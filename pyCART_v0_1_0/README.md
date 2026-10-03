# Σ DEEP SIGMA CARTOGRAPHY — pyLib 0.1.0

**Cartography for organizational coherence.** A traceable map of what decisions depend on.

An executable, offline-first Python add-on, not a graphic generator and not a new authority service.
This module models claims, events, evidence, authorities, dependencies, constraints, and uncertainty;
provides deterministic traversal and structural review; preserves original identities through reversible
folding; and archives versioned map editions. Human authorization remains outside this module.

## Install and run

Python **3.10+** is declared. See `verification/VALIDATION.md` for the interpreter actually tested.
The core has **zero third-party runtime dependencies**.

```bash
python -m pip install deepsigma_cartography-0.1.0-py3-none-any.whl
sigma-cartography demo --out cartography-demo
sigma-cartography validate cartography-demo/baseline.json
sigma-cartography assess cartography-demo/baseline.json --as-of 2026-10-03T12:00:00Z
sigma-cartography trace cartography-demo/baseline.json mission:readiness evidence:report --as-of 2026-10-03T12:00:00Z
sigma-cartography impact cartography-demo/baseline.json evidence:report --as-of 2026-10-03T12:00:00Z
sigma-cartography diff cartography-demo/baseline.json cartography-demo/candidate.json
```

From source: `python -m pip install -e .` then `python -m pytest -q`.
An already populated demo directory is rejected instead of silently overwritten.

## Python API

```python
from deepsigma_cartography import Atlas, assess, trace, impact, fold, EditionStore

atlas = Atlas.load("cartography-demo/baseline.json")
view = atlas.view(as_of="2026-10-03T12:00:00Z")
route = trace(view, "mission:readiness", "evidence:report")
report = assess(view)
affected = impact(view, "evidence:report")
summary = fold(view, by="layer")
assert summary.unfold().fingerprint == view.fingerprint

with EditionStore.create("my-map.sqlite3", atlas_id=atlas.id) as archive:
    edition = archive.append(atlas, recorded_at=view.as_of, expected_parent=None)
    archive.verify(expected_head=edition.edition_hash)
```

`Atlas` records are deeply immutable under normal Python API use; changes create another Atlas.
Input arrays are canonicalized by identity. Duplicate IDs, dangling endpoints, unknown predicates,
invalid confidence values, malformed JSON, duplicate JSON keys, and naive timestamps are rejected.
See `examples/quickstart.py` for construction without the demo.

## Capabilities

| Surface | Actual implementation |
|---|---|
| Terrain / legend | Typed Node, Edge, Evidence, Predicate; explicit scope and layer |
| PATHFINDER-oriented | Deterministic minimum-hop trace, incoming/outgoing traversal, dependencies, reverse impact, iterative cycle detection |
| RESONATOR-oriented | Eight structural finding codes, explicit expected-relationship coverage, separate recorded-reference metrics |
| COMPOSER / CERPA | Review and Patch-shaped **draft** dictionaries; no Apply function |
| VINCULUM | A proposed read-only JSON interchange envelope, **not a native plug-in** |
| Semantic folding | Group by layer/kind/scope; preserve every member/edge and source view; unfold after JSON round trip |
| Editions | SQLite, immutable snapshots through this API, parent-linked SHA-256, compare-and-swap, restart verification |
| Exports | Lossless canonical JSON/JSONL; spreadsheet-safe CSV; JSON-LD and N-Triples statement projections |
| Excel | Optional 11-tab workbook: Dashboard, C, E, R, P, A, Memory, Relationships, Evidence, Legend, Metadata |

Structural findings: `EVIDENCE_GAP`, `AUTHORITY_GAP`, `TEMPORAL_GAP`, `SEMANTIC_ORPHAN`,
`UNCERTAINTY`, `PROVENANCE_GAP`, `CONTRADICTION_RECORDED`, `DEPENDENCY_CYCLE`, plus
`COVERAGE_GAP` when explicit `CoverageRequirement` objects are supplied. That is **eight default
codes plus one opt-in coverage code**, not the full RESONATOR ten-gap taxonomy.

## Interpretation boundaries

A recorded map is not the territory. `observed`, `asserted`, `inferred`, `unknown`, and `retracted`
are explicit source declarations, not truth certifications. Missing confidence remains `None`; it
is never supplied as zero or one. Confidence is not relabeled as calibrated probability.

Every analytical operation uses an explicit timezone-aware `as_of`. Validity intervals are half-open
`[valid_from, valid_to)`; overdue review is `review_due <= as_of`. Missing time bounds mean the
source did not declare those bounds, not that the represented fact is timeless. Supersedes edges
are descriptive and do not silently expire older objects.

Impact is **structural reachability**, not predicted failure, severity, or causal proof. `depends_on`
points from dependent to dependency; `supports` points from support to dependent. Type/legend
semantics, not line appearance, determine propagation. A no-path result says `NO_RECORDED_ROUTE`,
not “no real dependency.” Bounded searches distinguish `SEARCH_BOUND_REACHED`.

Folding is a display summary. Grouping can create apparent paths across different members of the
same group. The library does **not** route on folded maps. Every original edge, including internal
edges, remains represented and the original MapView is embedded for lossless recovery.

The assessment counts live recorded evidence references within its declared one-hop support
scope. It does not verify evidence content or source reliability. A recorded authority link is not
proof of permission. An empty denominator returns `None` / `NOT EVALUATED`, never perfect coverage.
Contradictions are reported only when an explicit contradiction relation exists; prose is not
interpreted. A dependency cycle may be intentional and does not automatically fail a map.

## Integration

The supplied DeepSigma repository snapshot declares `deepsigma` 2.1.2 with `src/core/` and
Python 3.10+. This distribution intentionally does **not** ship a competing `core/__init__.py` or
`vinculum/__init__.py`. Install separately. The optional shim under `integration/core/cartography/`
can be copied into the host repo after review, with this distribution added as a dependency.

`from_memory_graph(mg, atlas_id=..., title=...)` consumes the inspected native
`MemoryGraph.to_json()` shape; original properties and timestamps remain in `source_record`.
Unknown relation kinds remain visible but do not acquire invented dependency semantics.

`cerpa_review(...)` and `patch_proposals(...)` match the inspected native Review/Patch constructors.
They are draft records only. A gap in one map does not establish drift: `drift_detected=False` is
accompanied by `metadata.drift_status="not_evaluated"`. A host must honor the draft boundary.

VINCULUM pyLib 0.7.0 migration notes preserve its existing kernels and introduce VinculumPipeline.
No source-compatible native Cartography hook or MERIDIAN API was available in the retrieved
materials. `vinculum_projection(...)` is therefore explicitly a **new proposed interchange
contract**. The package does not claim to be merged, deployed, or plug-and-play with that runtime.
See `docs/INTEGRATION.md` and `docs/REQUIREMENTS_TRACEABILITY.md`.

## Excel

The optional exporter uses **artifact_tool**, which must be provisioned separately; it is not a
base pip requirement. No openpyxl fallback is silently substituted.

```python
from deepsigma_cartography.workbook import export_workbook
export_workbook(view, "cartography.xlsx", report)
```

Or `sigma-cartography export baseline.json --as-of 2026-10-03T12:00:00Z --format xlsx --out map.xlsx`.
C/E/A contain only imported relevant records. R contains structural findings; P contains proposals.
An empty A sheet does not conceal an executed Apply—the module has no actuation API. The workbook
is a review projection; JSON/JSONL preserves complete attributes. No monthly graphic palette is
invented by this release; graph-image rendering is deliberately outside its scope.

## Archive trust model

SHA-256 checks byte/content integrity, **not identity, authorization, or truth**. The archive is
append-only through the supported API, not an immutable filesystem. SQLite writes are transactional;
chain/head corruption and stale parents fail closed. `open()` does not recreate a missing archive.
Use explicit `create()` only for initial provisioning. Retain the last head in an independently
trusted location and pass `expected_head` to detect whole-file rollback. A same-folder sidecar alone
is not an independent trust anchor. An attacker controlling both the database and trusted checkpoint
is outside this threat model. This is not Policy Fence, a signature service, anti-rollback hardware,
a multi-tenant access-control service, or an accredited records repository.

Scope and layer filters are **not security controls**. Attributes, endpoints, evidence, and topology
may contain sensitive information. Supply a separately authorized/redacted input upstream; never
use this package's view filters as a release or classification boundary.

## Project layout

`src/deepsigma_cartography/`: contracts, atlas, navigation, assessment, folding, editions, adapters,
exports, optional workbook, CLI, and explicit synthetic sample.
`tests/`: positive, negative, serialization, graph, archive, adapter, and CLI tests.
`docs/`: architecture, source traceability, integration, security/limits.
`verification/`: executed test evidence and package checks.

MIT license for this newly authored module. No proprietary source, third-party font, model weights,
credentials, or private signing keys are embedded. No network calls occur in the core runtime.
