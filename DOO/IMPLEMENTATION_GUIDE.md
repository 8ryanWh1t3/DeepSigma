# DOO Implementation Guide

## Goal

DOO is a semantic interchange model. It does not require an RDF-native runtime. A system is conformant when it preserves the meaning and identity of the DOO objects and relationships it claims to implement.

## Minimum portable Decision Episode

A portable episode should preserve:

1. `DecisionEpisode.identifier`
2. at least one `DecisionProblem`
3. zero or more `DecisionOption` objects considered
4. at least one `Decision`
5. participating `Actor` identities
6. decision time and concise `whySummary` when known
7. action and outcome links when execution is tracked

Governed environments should additionally preserve evidence, assumptions, authority, review state, patches, memory records, and provenance.

## Storage projections

### RDF / OWL
Use DOO classes and properties directly. Import only the modules needed by the deployment.

### Property graph
Map DOO classes to node labels and DOO object properties to typed edges. Preserve ontology IRIs as schema metadata so exports can reconstruct RDF without semantic loss.

### Relational
Use durable IDs as primary keys. Represent object properties with foreign keys or relationship tables. Keep ontology term IRIs in a schema registry rather than encoding semantics only in column names.

### JSON / event systems
Use `doo-context.jsonld` or equivalent URI mappings. Every event or object should carry stable identity, type, version, and references to related objects.

### Documents / spreadsheets
Represent each DOO object as an addressable row or record with stable IDs. Relationships must be explicit columns/links, not inferred only from visual proximity.

### Agents / AI systems
Treat DOO types as contract objects. Agents may propose claims, options, reviews, or patches, but authority remains externally asserted and must not be inferred solely from model output.

## Profiles

- **Core profile:** Core only. Basic decision capture and interchange.
- **Evidence profile:** Core + Evidence. Traceable claims and assumptions.
- **Governed profile:** Core + Evidence + Authority + Lifecycle. Auditable decision operations.
- **Replay profile:** Governed profile + Memory + PROV-O alignment. Long-lived institutional decision memory.
- **Coherence Ops profile:** Full DOO + `doo-coherenceops.ttl`. Optional Deep Sigma implementation mapping.

## Conformance principle

A system does not need to expose RDF to users. It does need to preserve the semantics required to round-trip its declared DOO profile without silently changing identity, authority, evidence, or lifecycle state.
