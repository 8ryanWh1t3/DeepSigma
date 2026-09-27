# Decision Operations Ontology (DOO) v0.3 — Portable Interoperability Draft

DOO is a vendor-neutral RDF/OWL vocabulary for representing how decisions are framed, supported, authorized, made, executed, reviewed, corrected, and remembered.

## Architectural rule

**DOO standardizes how a decision exists. Operating models decide how an organization uses it.**

A conformant implementation can use RDF, a property graph, SQL, JSON, event stores, documents, spreadsheets, or platform-native objects. RDF does not have to be the runtime; the semantics must survive projection and round-trip.

## What changed in v0.3

- Added **Decision Anatomy** as a separate reusable module.
- Defined four machine-readable **conformance profiles**: Core, Evidence, Governed, Replay.
- Split SHACL into profile-specific validation graphs.
- Strengthened PROV-O alignment and DecisionPacket/Bundle semantics.
- Added explicit interoperability metadata and episode membership traversal.
- Converted lifecycle/status vocabularies into SKOS concept schemes while preserving OWL individuals.
- Added minimal and governed examples, JSON-LD, SPARQL queries, migration mappings, manifest, checksums, and a validation harness.
- Preserved Coherence Ops as an **optional external profile**, not a dependency of universal DOO.

## Universal decision spine

`Context → Problem → Evidence/Assumptions → Options → Decision → Authority → Action → Outcome → Review → Drift → Patch → Memory`

## Modules

| File | Purpose | Universal? |
|---|---|---|
| `doo-core.ttl` | Stable identity, episodes, problems, options, decisions, actors, actions, outcomes | Yes |
| `doo-anatomy.ttl` | Intent, rationale, expected/observed outcomes, risk, tradeoffs, dependencies | Yes / optional by profile |
| `doo-evidence.ttl` | Claims, evidence, assumptions, sources, uncertainty, contradiction | Yes / optional |
| `doo-authority.ttl` | Authority, scope, roles, approvals, constraints, policy basis | Yes / optional |
| `doo-lifecycle.ttl` | State, review, drift, patch, invalidation, supersession | Yes / optional |
| `doo-memory.ttl` | Lineage, reflection, drift records, memory graphs, decision packets | Yes / optional |
| `doo-provenance.ttl` | W3C PROV-O alignment | Yes / recommended |
| `doo-profiles.ttl` | Machine-readable conformance profiles | Yes |
| `doo-shapes*.ttl` | Profile-specific SHACL contracts | Yes / validation |
| `doo-all.ttl` | Convenience import of all vendor-neutral semantic modules | Yes |
| `doo-coherenceops.ttl` | Optional Coherence Ops mapping | No — extension profile |

## Conformance profiles

- **CORE** — portable decision episode and decision anatomy.
- **EVIDENCE** — CORE + claims, evidence, assumptions, uncertainty.
- **GOVERNED** — EVIDENCE + represented authority and lifecycle state.
- **REPLAY** — GOVERNED + memory records and PROV-O lineage.

## Design invariants

1. **Decision is the persistent object.** UI surfaces are projections.
2. **Identity survives system boundaries.** Moving a decision must not silently create a new decision.
3. **Authority is represented, never inferred or conferred by the ontology.**
4. **Evidence and assumptions remain distinguishable.**
5. **Alternatives can be preserved even when rejected.**
6. **Corrections append lineage; they do not erase historical reasoning.**
7. **External standards are reused where appropriate.** PROV-O provides provenance primitives.
8. **Vendor extensions cannot redefine universal DOO terms.**

## Namespace

The draft uses `https://decisionoperations.org/ontology/...` as a **proposed** neutral namespace. Before 1.0, bind the namespace to a project-controlled domain or persistent identifier and make ontology IRIs dereferenceable.

## Licensing

For broad reuse, CC0 is the recommended licensing direction, but this draft does **not** assert a public license. Confirm project/legal approval before public release.

## Coherence Ops

Coherence Ops remains an operating model. `doo-coherenceops.ttl` maps DOO into its vocabulary but is not required for DOO conformance.
