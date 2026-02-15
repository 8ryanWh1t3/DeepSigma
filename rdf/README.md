# RDF Layer (A = Triples/SPARQL)

This folder defines the canonical semantic layer for the repo using RDF + SPARQL.

## Standards used

- RDF / RDFS / OWL
- - SKOS (controlled vocabulary)
  - - PROV-O (provenance)
    - - SHACL (validation)
     
      - ## Design rules
     
      - - SharePoint remains the artifact store (system of record).
        - - RDF provides the meaning overlay via stable URIs.
          - - Use Named Graphs for sealing (immutable decision episodes; patch rather than overwrite).
           
            - ## Folders
           
            - - `ontology/` — Canonical classes + predicates (Turtle), including the Claim Primitive module
              - - `shapes/` — SHACL constraints enforcing data quality
                - - `examples/` — Sample instance graphs
                  - - `queries/` — SPARQL queries that prove "why retrieval ≤ 60s"
                    - - `mappings/` — SharePoint → RDF mapping notes + sample I/O
                      - - `pipelines/` — Extractor + connector contracts (design docs)
                        - - `diagrams/` — Mermaid diagrams (architecture)
                          - - `sample_data/` — Toy data for testing
                           
                            - ## Claim Primitive (v1.0)
                           
                            - The Unified Atomic Claim model is fully represented in the RDF layer:
                           
                            - | Artifact | Path |
                            - |----------|------|
                            - | OWL ontology module | `ontology/claim_primitive.ttl` |
                            - | SHACL validation shapes | `shapes/claim_primitive.shacl.ttl` |
                            - | Sample instance graph | `examples/claim_primitive_instance.ttl` |
                            - | SPARQL query pack (10 queries) | `queries/claim_queries.rq` |
                            - | JSON Schema (source of truth) | `../specs/claim.schema.json` |
                           
                            - The `ds:AtomicClaim` class extends `ds:Claim` from `coherence_ops_core.ttl`, preserving backward compatibility with existing SPARQL queries.
                           
                            - ## Quick start (conceptual)
                           
                            - 1. Export or access SharePoint items (docs + metadata).
                              2. 2. Extract structured nodes: Claim, Evidence, Source, Decision, Assumption, Policy, Drift, Patch.
                                 3. 3. Emit RDF triples (Turtle).
                                    4. 4. Validate with SHACL constraints.
                                       5. 5. Query with SPARQL and ground LLM responses from the retrieved subgraph.
                                         
                                          6. ---
                                         
                                          7. ## Add-ons from rdf_module_v0.1
                                         
                                          8. # RDF Module — Coherence Ops Semantic Substrate
                                         
                                          9. This module provides the semantic layer that transitions KM from SharePoint (document-centric)
                                          10. to RDF (meaning-centric).
                                         
                                          11. - SharePoint = blob storage (documents + basic metadata)
                                              - - RDF = meaning graph (claims, evidence, provenance, authority, drift, patch)
                                               
                                                - ## What this enables
                                               
                                                - - Truth · Reasoning · Memory enforcement via structure (ontology + constraints)
                                                  - - Drift → Patch automation via graph-native relationships
                                                    - - Executive retrieval (DLR "why" in ≤ 60s) via SPARQL query pack
                                                      - - LLM grounding via subgraph retrieval (graph-first context)
                                                       
                                                        - ## Contents
                                                       
                                                        - - `ontology/` Ontology (TTL), prefixes, SHACL constraints ("constitution layer")
                                                          - - `mappings/` SharePoint → RDF mapping notes + sample I/O
                                                            - - `queries/` SPARQL executive query pack
                                                              - - `pipelines/` Extractor + connector contracts (design docs)
                                                                - - `examples/` Walkthroughs and demo narratives
                                                                  - - `diagrams/` Mermaid diagrams (architecture)
