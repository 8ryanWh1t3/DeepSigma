# Deep Sigma pyOntology v0.1.0 — Build Report

## Status

**PASS — MVP federation contract established.**

## Measured source ontology load

| Module | Version | Triples | Classes | Object Properties | Datatype Properties | Named Individuals |
|---|---:|---:|---:|---:|---:|---:|
| Coherence Ops Core | 2.0.0 | 825 | 118 | 19 | 13 | 26 |
| Coherence Ops 6 Lenses | 2.1.0 | 358 | 5 | 8 | 11 | 27 |

## Verification

- Unit/integration tests: **10/10 PASS**
- Python compileall: **PASS**
- Real Coherence Ops federation validation: **PASS**
- Unresolved cross-module collisions in seeded Core + Lenses example: **0**
- Canonical graph fingerprint repeatability on real ontology: **PASS**
- Blank-node fingerprint repeatability: **PASS**
- Concept creation gate: `Decision` against the Lenses module returns **REUSE**
- CI gate exit code for attempted duplicate `Decision`: **3** (blocked for governance review)

## Non-blocking source warnings

The core ontology contains repeated human-readable labels for distinct domain events (for example, domain-specific expiry/patch events). pyOntology reports these as internal warnings but does not treat them as federation failures because the URIs remain distinct and locally governed.

## v0.1.0 boundary

This build deliberately stops before embedding/vector similarity, remote triplestore adapters, signed authority decisions, and automated ontology merge. The deterministic registry/federation contract is established first.
