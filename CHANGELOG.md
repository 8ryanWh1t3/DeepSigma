# Changelog

All notable changes to Σ OVERWATCH / DeepSigma will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-02-16 — "Living Memory"

### Added — Money Demo (Drift → Patch in One Command)

- **Money Demo script** (`coherence_ops/examples/drift_patch_cycle.py`): One-command Drift → Patch loop producing 8 deterministic artifacts (3 reports, 3 MG snapshots, diff, Mermaid diagram)
- **CI contract gate**: Money Demo smoke test runs on every push to `main` and every PR (`.github/workflows/ci.yml`)
- **Coherence SLO definitions**: 8 enforceable SLOs aligned to Money Demo outputs (`metrics/coherence_slos.md`)
- **Smoke test suite**: 16 pytest tests covering artifacts, score monotonicity, diff integrity, and Mermaid output (`tests/test_money_demo.py`)
- **Evidence file**: `examples/demo-stack/MONEY_DEMO_EVIDENCE.md` with deterministic scores, artifact manifest, and contract checks
- **Issue #8 closeout**: `docs/issue_closeouts/issue_8_demo_loop.md`

### Changed

- `HERO_DEMO.md` — Added "Run the Money Demo" section with deterministic score output
- `metrics/coherence_slos.md` — Updated to v1.1.0 with Money Demo SLOs
- `coherence_ops/__init__.py` — Version bump to 0.3.0
- `pyproject.toml` — Version bump to 0.3.0

### Scores (Deterministic)

| State | Score | Grade |
|-------|-------|-------|
| Baseline | 90.00 | A |
| Drift | 85.75 | B |
| After Patch | 90.00 | A |

## [0.2.0] — 2026-02-15

### Added — Unified Atomic Claims

- **Claim Primitive v1.0**: `specs/claim.schema.json` — Universal Atomic Claim JSON Schema with confidence, status light, half-life, seal, graph edges, and provenance chain
- - **Claim-Native DLR v1.0**: `specs/dlr.schema.json` — Refactored Decision Lineage Record composing from claim references with rationale graph
  - - **Claim Primitive Example**: `llm_data_model/03_examples/claim_primitive_example.json` — SIGINT credential-stuffing scenario (CLAIM-2026-0001)
    - - **DLR Claim-Native Example**: `llm_data_model/03_examples/dlr_claim_native_example.json` — AccountQuarantine decision with 3 claims
      - - **Docs**: `docs/19-claim-primitive.md`, `docs/20-dlr-claim-native.md`
        - - **Wiki**: `wiki/Unified-Atomic-Claims.md` with sidebar navigation update
          - - **Mermaid Diagrams 27-28**: Claim Primitive (5 diagrams) and DLR Claim-Native (5 diagrams)
           
            - ### Added — RDF Semantic Layer Integration
           
            - - **OWL Ontology Module**: `rdf/ontology/claim_primitive.ttl` — 7 classes, 5 enumerations, 12 object properties, 25+ datatype properties under `ds:` namespace
              - - **SHACL Shapes**: `rdf/shapes/claim_primitive.shacl.ttl` — 6 node shapes enforcing JSON Schema constraints
                - - **Instance Graph**: `rdf/examples/claim_primitive_instance.ttl` — CLAIM-2026-0001 as RDF triples
                  - - **SPARQL Query Pack**: `rdf/queries/claim_queries.rq` — 10 queries (status light, triage, WHY, contradictions, expired half-lives, dependencies, supersession, truth type audit, classification, seal integrity)
                    - - **Framework Ontology**: 3 new `coh:Pattern` individuals in `rdf/coherence-ops-ontology.ttl` (ClaimPrimitive, ClaimNativeDLR, UnifiedAtomicClaims)
                     
                      - ### Added — New Schemas
                     
                      - - **Canon Schema**: `specs/canon.schema.json` — Promotes claim IDs from DLR to long-term blessed memory
                        - - **Drift Schema**: `specs/drift.schema.json` updated with claim-native drift detection
                          - - **Retcon Schema**: `specs/retcon.schema.json` — Retroactive claim correction operations
                            - - **Patch Schema**: `specs/patch.schema.json` — Patch operations on claim versions
                             
                              - ### Added — Code Integration
                             
                              - - **DLR Builder**: `coherence_ops/dlr.py` — `ClaimNativeDLRBuilder` class producing claim-native DLRs from sealed episodes
                                - - **Memory Graph**: `coherence_ops/mg.py` — `CLAIM` added as `NodeKind`, `add_claim()` method, claim-aware query support
                                  - - **IRIS Engine**: `coherence_ops/iris.py` — Full implementation wired to DLR/MG for WHY, WHAT_CHANGED, WHAT_DRIFTED, RECALL, STATUS resolution
                                   
                                    - ### Added — Tests
                                   
                                    - - **SHACL Validation Test**: `tests/test_shacl_claim.py` — Validates RDF instance against SHACL shapes
                                      - - **JSON Schema Validation Test**: `tests/test_schema_claim.py` — Validates JSON examples against JSON Schema specs
                                       
                                        - ### Changed
                                       
                                        - - `rdf/MANIFEST.md` — Added Claim Primitive section
                                          - - `rdf/README.md` — Added Claim Primitive documentation table
                                            - - `mermaid/README.md` — Added diagrams 27-28 to catalogue
                                              - - `wiki/_Sidebar.md` — Added Claim Schema, DLR Schema, Unified Atomic Claims links
                                                - - `coherence_ops/__init__.py` — Exports ClaimNativeDLRBuilder
                                                 
                                                  - ## [0.1.0] — 2026-02-13
                                                 
                                                  - ### Added
                                                 
                                                  - - **Engine**: supervisor scaffold, degrade ladder, policy loader
                                                    - - **Coherence Ops**: DLR builder, reflection session, drift signal collector, memory graph, auditor, scorer, reconciler, CLI (`coherence audit|score|mg|demo`)
                                                      - - **Verifiers**: read-after-write, invariant check stubs
                                                        - - **Specs**: JSON Schemas for Episode, DTE, Action Contract, Drift, Policy Pack
                                                          - - **Policy Packs**: versioned enforcement bundles with hash verification
                                                            - - **Tools**: `run_supervised.py`, `validate_examples.py`, `drift_to_patch.py`, `replay_episode.py`
                                                              - - **Adapters**: MCP JSON-RPC scaffold, OpenClaw skill runner scaffold, OTel exporter placeholder
                                                                - - **Dashboard**: interactive monitoring demo (HTML + React build)
                                                                  - - **LLM Data Model**: canonical record envelope, 6 record types, schemas, mappings, validation, retrieval, ontology
                                                                    - - **RDF Semantic Layer**: OWL ontology (Core 8 classes), SHACL shapes, SPARQL executive queries, SharePoint→RDF mappings
                                                                      - - **Mermaid Diagrams**: 26 diagrams covering architecture, runtime, schemas, coherence ops, LLM data model, and RDF layer
                                                                        - - **Examples**: demo-stack (4 scenarios), episodes, drift events, DTE packs, MCP samples
                                                                          - - **Docs**: 16 documentation files covering all modules
                                                                            - - **Wiki**: 48 pages covering concepts, schemas, integrations, governance, and visual documentation
                                                                             
                                                                              - ### Infrastructure
                                                                             
                                                                              - - **CI**: GitHub Actions with pytest (3.10/3.11/3.12), ruff lint, schema validation, and integration tests
                                                                                - - **Packaging**: `pyproject.toml` with console scripts (`overwatch`, `overwatch-validate`, `coherence`)
                                                                                  - - **Repo Governance**: SECURITY.md, CODEOWNERS, Dependabot, issue/PR templates, CONTRIBUTING.md
                                                                                    - - **Testing**: unit tests (degrade ladder, policy loader) + integration test (full coherence pipeline end-to-end: episode → seal → score → drift → audit → reconcile → patch → re-score)
                                                                                     
                                                                                      - [0.2.0]: https://github.com/8ryanWh1t3/DeepSigma/compare/v0.1.0...HEAD
                                                                                      - [0.1.0]: https://github.com/8ryanWh1t3/DeepSigma/releases/tag/v0.1.0
