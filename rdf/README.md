# RDF Layer (A = Triples/SPARQL)

This folder defines the canonical semantic layer for the repo using RDF + SPARQL.

## Standards used
- RDF / RDFS / OWL
- SKOS (controlled vocabulary)
- PROV-O (provenance)
- SHACL (validation)

## Design rules
- SharePoint remains the artifact store (system of record).
- RDF provides the meaning overlay via stable URIs.
- Use Named Graphs for sealing (immutable decision episodes; patch rather than overwrite).

## Folders
- ontology/: canonical classes + predicates (Turtle)
- shapes/: SHACL constraints enforcing data quality
- examples/: sample instance graphs
- queries/: SPARQL queries that prove "why retrieval ≤60s"

---

## Add-ons from rdf_module_v0.1

# RDF Module – Coherence Ops Semantic Substrate

This module provides the semantic layer that transitions KM from SharePoint (document-centric)
to RDF (meaning-centric).

- SharePoint = blob storage (documents + basic metadata)
- RDF = meaning graph (claims, evidence, provenance, authority, drift, patch)

## What this enables
- Truth · Reasoning · Memory enforcement via structure (ontology + constraints)
- Drift → Patch automation via graph-native relationships
- Executive retrieval (DLR “why” in ≤ 60s) via SPARQL query pack
- LLM grounding via subgraph retrieval (graph-first context)

## Contents
- `ontology/`   Ontology (TTL), prefixes, SHACL constraints (“constitution layer”)
- `mappings/`   SharePoint → RDF mapping notes + sample I/O
- `queries/`    SPARQL executive query pack
- `pipelines/`  Extractor + connector contracts (design docs)
- `examples/`   Walkthroughs and demo narratives
- `diagrams/`   Mermaid diagrams (architecture)

## Quick start (conceptual)
1. Export or access SharePoint items (docs + metadata).
2. Extract structured nodes: Claim, Evidence, Source, Decision, Assumption, Policy, Drift, Patch.
3. Emit RDF triples (Turtle).
4. Validate with SHACL constraints.
5. Query with SPARQL and ground LLM responses from the retrieved subgraph.