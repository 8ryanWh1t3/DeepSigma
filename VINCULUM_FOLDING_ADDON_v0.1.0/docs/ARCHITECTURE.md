# Architecture decision: an additive sidecar, not a replacement engine

## Boundary

```
Existing VINCULUM pyLib 0.7.0
  original job -> original pipeline -> original evaluation
                              |
                    serialization snapshot (read only)
                              v
                  vinculum_folding.from_pipeline
                              |
           TIME / WORDS / NUMBERS episode + original host capture
                              |
           explicit folds + four JIT assessments + evidence
                              |
     inspect / unfold / traverse / replay / draft review handoff
                              |
         JSON view contract + optional local snapshot journal
```

This is a newly implemented extension of the conversation's conceptual design.
The original v0.7.0 material does not claim to implement this entire add-on.

## Module boundaries

`model.py` validates versioned episode snapshots and exact values. `adapter.py`
copies the source-inspected host serialization API without invoking its engine.
`engine.py` produces structural/declared-scope findings and inspector projections.
`navigation.py` provides version-pinned graph focus, return paths and replay.
`journal.py` provides explicit local SQLite persistence. `export.py` writes
non-overwriting sidecar bundles and validates reproducible projections.
`demo.py` and `cli.py` provide the synthetic demonstration and local commands.

## Three aspects are not three scoring sides

TIME is either an explicitly declared aspect or a projection of a host scope
window. WORDS preserve an expression and separately declared scope. NUMBERS
preserve an exact range, unit, concept and method. They share an episode identity;
they are not assumed to share physical direction, certainty, scale or ontology.
Rightward progression is a presentation convention, not a kernel law.

The host's L/M sides, examination orders, P/D descriptors and pair-owned hinges
are independent of the four JIT lenses. They are copied, not reinterpreted.

## The four JIT lenses

1. Legacy of Precision: exact wording, unit, scope and lineage examination.
2. Density of Exposure: evidence/coverage examination with shared-root disclosure.
3. Matrix of Awareness: attributed Evaluation, Potency, Activity and viewpoint.
4. Ontological Grade: user-defined Grade-1 Vector (natural/physically grounded)
   versus Grade-2 Bivector (constructed/relational artifact), or UNSPECIFIED.

The labels in item 4 are project categories. No exterior-algebra operation is
performed. A physical referent, a number about it and the text recording it remain
distinct. A representation can accurately describe reality while remaining a
representation. No grade is a reliability rank.

Every local fold includes all four lenses. A supported/challenged assessment
requires an assessor, rationale and evidence references. The checks verify these
fields and references, not the truth of their contents. Missing assessments stay
UNASSESSED. Missing evidence locations produce a separate finding, even when an
input assessment calls itself SUPPORTED.

## Fold and counterfold

A fold is a directed, explicit relationship with rationale. DERIVED_FROM and
DEPENDS_ON point from the dependent node to its premise. SELECTED_PAIR retains
host left/right orientation. COUNTERFOLD records an alternative relation without
selecting a winner. Ordinary relationship cycles can be navigated with bounded
visited-node traversal; graph reach is not automatically a causal inference.

The v0.1 scope-expansion check is intentionally narrow: a WORDS/EXHAUSTIVE node
DERIVED_FROM a WORDS/RECORDED node generates a review finding. It never parses
arbitrary prose to invent those scope labels. Temporal checks evaluate the
explicit strict-before relation only. Existing host math/codec results are not
replaced with these checks.

## Identity and projection

Episode IDs persist across revisions. Revision N>1 names its predecessor digest.
Each cross-episode link names the exact target episode, revision and node.
Original source IDs, pair IDs and representation IDs remain in host_capture.
Local projection IDs use r/, t/ and p/ prefixes without changing host identity.
Every source annotation, assessment and event is recorded data, not a statement
that the producer's identity was authenticated.

Episode digests cover all content, including non-scored context. This is snapshot
identity, not a new numeric or pipeline scoring fingerprint. Original host
fingerprints are preserved verbatim. Reordering an array changes episode content
identity; object-key order does not.

## World / Studio / Trinity / CERPA

VINCULUM reads the view model. Studio or another host prepares edits as a new
snapshot. PATHFINDER can consume version-pinned dependency links; RESONATOR can
supply attributed assessment material; COMPOSER can consume a draft review or
patch request under its own governance. These are integration boundaries, not
connections supplied in this package.

CERPA references preserve CLAIM -> EVENT -> REVIEW -> PATCH -> APPLY identity.
The add-on creates only DRAFT_REVIEW_INPUT handoffs. DLR, RS, DS and MG references
carry source pointers rather than synthesized institutional records. No operation
in this package converts a link, score or checkbox into authority. A linked APPLY
record does not assert that an outcome succeeded.
