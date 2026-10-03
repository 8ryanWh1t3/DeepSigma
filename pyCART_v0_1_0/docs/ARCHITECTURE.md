# Architecture and API contract — 0.1.0

## Position

Cartography is a representation/analysis module within Deep Sigma, not a replacement for the
Semantic Kernel, LatticeDB, PATHFINDER, RESONATOR, COMPOSER, CERPA, or VINCULUM.

The analytical path is `source records -> Atlas -> time-bound MapView -> trace / assess / fold ->
review artifacts / editions`. A proposed change returns to the host COMPOSER/CERPA workflow.
This package never makes an operational change authoritative.

## Contracts

`Node`: globally distinct ID; label; extensible kind; layer; analytical scope; declared status;
optional confidence, evidence references and time bounds; review due time; immutable JSON attributes.
`Edge`: distinct ID; stored source/predicate/target; status; optional confidence/evidence/time bounds;
immutable JSON attributes. Parallel edges are allowed because distinct assertions/provenance may
share endpoints. Endpoints must exist.
`Evidence`: distinct ID; source locator; optional recorded content hash and time bounds.
`Predicate`: explicit definition; optional source/target kinds; dependency orientation;
optional evidence-relation designation. Unknown predicates require explicit registration.

Default status is `asserted`: the caller declares a representation, not an observation, verification,
or probability. Missing confidence is `None`. Input arrays sort by identity, while semantically
ordered arrays inside attributes preserve their order. Canonical JSON uses Python JSON with sorted
keys, ASCII escapes, compact separators and finite numbers. **It does not claim RFC 8785 conformance.**
Fingerprints include complete attributes, legend, evidence, and declared time/status data.

`MapView` binds an Atlas projection to UTC as_of, source fingerprint, and analytical filters. Changes
to as_of change the view identity. Scope/layer filtering is induced-subgraph selection, not redaction.
Referenced Evidence is retained even when expired so the assessment can expose the deficit.

## Time

All supplied timestamps must have a timezone; UTC output is normalized to microsecond precision.
Validity is `[valid_from,valid_to)`. `review_due <= as_of` is overdue. Expiration removes a node and
its incident edges from an active view. Review-due does not remove the node; it produces a finding.
Unbounded records have unspecified validity, not a promise of timelessness. This is not full
bitemporal querying. Map edition `recorded_at` is an archive timestamp, not real-world event time.

## Navigation

`trace(view,source,target,direction='out',predicates=None,max_depth=None)` uses breadth-first search.
Tie ordering is neighbor ID, then edge ID. `in` and `both` retain stored direction in every step.
`dependencies` traverses each predicate's dependent-to-dependency orientation; `impact` reverses it.
Cycles use iterative strongly connected components. No recursive Python stack is required.

`NO_RECORDED_ROUTE` means no recorded route in this view. `SEARCH_BOUND_REACHED` means the depth
bound left reachable neighbors unexplored. A found path is `RECORDED_ROUTE` even if other branches
would be longer than the search bound. Paths include declared inference/unknown status when those
edges are included; they are not certified dependency chains.

Complexity: adjacency/BFS/SCC are O(V+E), excluding sorting and serialization. `reach` returns a
witness route for every reachable node; on long chains total output can be O(V^2). Use `trace` for
one target or `max_depth` to bound exploration. No enterprise-scale performance guarantee is made.

## Structural assessment

Eight default codes plus optional `COVERAGE_GAP` are implemented. Findings are artifacts, not
people scores. Evidence metrics measure recorded live references, not factual validity, independent
sources, calibration, or probability. Evidence search is direct node references plus one hop through
explicit evidence relations and their source-node references. It does not treat arbitrary dependency
chains as evidential proof. Authority-reference metrics do not validate grants or actor identities.
A cycle is a review condition, not a proven contradiction. Natural-language contradiction extraction,
SKOS reasoning, OWL entailment, legal compliance, and scalar enterprise coherence scores are absent.

## Folding

Group by kind/layer/scope. Store every member ID; group links by source group, predicate, target
group and epistemic status; retain every original edge ID and internal edge. The original complete
MapView and its fingerprint are included. `FoldedMap.from_dict` recomputes and compares the summary.
`unfold` returns the original view. **No navigation method accepts a FoldedMap.** That avoids false
transitive paths created by grouping unrelated members into a shared display node.

## Editions

The application archive has one atlas identity. `create` exclusively provisions a new file; `open`
uses SQLite `mode=rw`, so a missing archive never becomes a fresh one implicitly. `append` requires
an explicit expected parent. It verifies the whole chain inside a `BEGIN IMMEDIATE` transaction,
inserts a full snapshot, advances the head, reads and verifies the rows, and commits. No update or
delete method is exposed. Database ownership remains a host trust assumption.

A full-file rollback requires an independently trusted expected head to detect. A hash chain does
not authenticate an operator and cannot protect itself from a host that can rewrite both data and
its trusted checkpoint. Storage write failures propagate. No durability success is returned merely
because a storage object exists. SQLite commit durability still depends on host/OS/filesystem behavior.

## Interchange

JSON and JSONL are the canonical lossless interchange. CSV quotes formula-leading literal text and
ships a canonical atlas.json alongside it. RDF projections reify each edge as rdf:Statement with
status and complete record JSON; they do not publish inferred edges as unqualified base triples.
JSON-LD uses inline context terms; it performs no remote context retrieval. Excel is optional and
uses artifact_tool. Existing upstream parser/engine implementations are not retuned.
