# pyOntology Architecture

## Design invariant

**Local ontology. Enterprise meaning.**

pyOntology is a federation layer, not a master ontology. Domain teams may own bounded modules, but the fabric governs how those modules discover, reuse, specialize, bridge, version, and validate shared meaning.

## Runtime layers

1. **OntologyModule** — loads RDF/OWL/SKOS and extracts module metadata + term inventory.
2. **SemanticRegistry** — SQLite-backed registry of modules, terms and accepted bridges.
3. **SemanticFabric** — cross-module search, collision detection, concept creation gates and bridge discovery.
4. **Validation** — module/fabric invariants; optional SHACL.
5. **Diff** — graph + term-level change detection for drift/version governance.
6. **CLI** — inspect, validate, search, collision scan, bridge discovery, diff.

## Human authority boundary

pyOntology may propose `REUSE`, `LINK`, `SPECIALIZE`, `REVIEW`, or `CREATE`.
It must not autonomously declare two enterprise terms equivalent. Proposed bridges remain `PROPOSED` until explicitly accepted.

## Silo-prevention flow

```text
REQUEST NEW CONCEPT
      |
      v
SEARCH ENTERPRISE FABRIC
      |
      +--> exact meaning exists ------> REUSE
      |
      +--> high similarity -----------> LINK / human review
      |
      +--> narrower local meaning ----> SPECIALIZE
      |
      +--> ambiguous neighborhood ----> REVIEW
      |
      `--> no material overlap -------> CREATE
```

## Deep Sigma placement

```text
DSAL          common machine language
DKO           portable operational knowledge
pyOntology    semantic federation + collision prevention
PATHFINDER    traversal / relationship control surface
RESONATOR     semantic comparison + coherence analysis
COMPOSER      governed semantic change
CERPA         claim/evidence/review/patch/authority loop
VINCULUM      inspection and replay
```
