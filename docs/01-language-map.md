# Language Map — LinkedIn Content → Repository Code

If you found this repository through Deep Sigma's LinkedIn content, this page maps the concepts you've read about to their implementations in code.

---

## How the Pieces Fit

```
Deep Sigma           ← brand / research program / body of work
└─ Coherence Ops     ← the operational framework (methodology)
   └─ Σ OVERWATCH    ← the runtime engine (software)
```

**Deep Sigma** is the brand. **Coherence Ops** is the framework. **Σ OVERWATCH** is the engine that executes it.

LinkedIn content primarily uses "Coherence Ops" and "Deep Sigma" language. This repository implements it as "Σ OVERWATCH" with a `coherence_ops/` library.

---

## Concept → Code Map

### Core Framework

| LinkedIn Concept | Repo Location | Status |
|-----------------|---------------|--------|
| DLR (Decision Lineage Record) | `coherence_ops/dlr.py` | ✅ Implemented + tested |
| RS (Reasoning Summary) | `coherence_ops/rs.py` | ✅ Implemented + tested |
| DS (Drift Scan) | `coherence_ops/ds.py` | ✅ Implemented + tested |
| MG (Memory Graph) | `coherence_ops/mg.py` | ✅ Implemented + tested |
| Coherence Score | `coherence_ops/scoring.py` | ✅ Implemented + tested |
| Drift → Patch loop | `tools/drift_to_patch.py` | ✅ Implemented |
| Seal / Sealing | `specs/episode.schema.json` | ✅ Schema + runtime |
| Claim–Evidence–Source chain | `rdf/ontology/`, `llm_data_model/` | ✅ Schema + ontology |
| Claim Primitive (atomic truth unit) | `specs/claim.schema.json`, `coherence_ops/dlr.py` | ✅ Schema + runtime |
| Canon (blessed claim memory) | `specs/canon.schema.json` | ✅ Schema |
| Retcon (retroactive correction) | `specs/retcon.schema.json` | ✅ Schema |
| Claim-Native DLR | `specs/dlr.schema.json`, `coherence_ops/dlr.py` | ✅ Schema + builder |
| Provenance | `rdf/queries/`, `coherence_ops/mg.py` | ✅ Graph + SPARQL |
| Truth–Reasoning–Memory | All four pillars + schemas | ✅ Distributed across pillars |

### Runtime Architecture

| LinkedIn Concept | Repo Location | Status |
|-----------------|---------------|--------|
| AL6 (6 dimensions of agentic reliability) | `README.md`, `docs/02-core-concepts.md` | ✅ Documented |
| DTE (Decision Timing Envelope) | `specs/dte.schema.json` | ✅ Full schema |
| Degrade Ladder | `engine/degrade_ladder.py` | ✅ Implemented + tested |
| Action Contracts (blast radius, idempotency, rollback) | `specs/action_contract.schema.json` | ✅ Full schema |
| DecisionEpisode | `specs/episode.schema.json` | ✅ Full schema + examples |
| Policy Packs | `policy_packs/` | ✅ Schema + versioned packs |
| Verification / Verifiers | `verifiers/` | ✅ Read-after-write + invariants |

### Operational Concepts

| LinkedIn Concept | Repo Location | Status |
|-----------------|---------------|--------|
| PRIME (threshold gate) | `coherence_ops/prime.py` | 🔜 Planned — Phase 1 |
| IRIS (operator interface) | `coherence_ops/iris.py`, `specs/iris_query.schema.json`, `docs/18-iris.md` | ✅ Implemented — claim-graph queries |
| FranOPS (franchise operations mode) | `coherence_ops/modes/franops.py` | 🔜 Planned — Phase 3 |
| IntelOps (intelligence operations mode) | `coherence_ops/modes/intelops.py` | 🔜 Planned — Phase 3 |
| ReflectionOps (reflection operations mode) | `coherence_ops/modes/reflectionops.py` | 🔜 Planned — Phase 3 |
| CTI (Coherence Threat Index) | `coherence_ops/scoring.py` (internal) | ⚡ Exists internally, being promoted to first-class |
| DAT (Dynamic Assertion Testing) | `tools/dat.py` | 🔜 Planned — Phase 4 |
| DDR (Deep Dive Review) | `tools/ddr.py` | 🔜 Planned — Phase 4 |
| ITCO (Integrated Truth & Coherence Ops) | — | 🔜 Planned — Phase 4 |
| Temperature regulation | `coherence_ops/scoring.py` | 🔜 Planned — Phase 4 |
| Assumption TTL / Half-life | `specs/dte.schema.json` (TTL fields) | ✅ Schema-level |
| Prompt-to-Coherence Translator | `tools/prompt_translator.py` | 🔜 Planned — Phase 5 |
| Portfolio Management | `coherence_ops/portfolio.py` | 🔜 Planned — Phase 5 |

### Narrative & Metaphors

| LinkedIn Concept | Repo Location | Notes |
|-----------------|---------------|-------|
| Stark Principle | `coherence_ops/README.md` | Referenced in docs |
| Ferrari / Chassis | `GLOSSARY.md` | Positioning metaphor — see glossary |
| Iceberg Model | `GLOSSARY.md` | Enterprise AI stack model — see glossary |
| Binary-to-Diamond | `GLOSSARY.md` | Decision refinement model — see glossary |
| MU-TH-UR | `GLOSSARY.md` | Alien (1979) structural analogy — see glossary |
| Institutional Memory | `coherence_ops/mg.py` | MG is the implementation of this concept |
| 42 | Everywhere | If you have to ask, you're not ready |

### Integrations

| LinkedIn Concept | Repo Location | Status |
|-----------------|---------------|--------|
| MCP (Model Context Protocol) | `adapters/mcp/` | ✅ Scaffold |
| OpenClaw | `adapters/openclaw/` | ✅ Scaffold |
| OpenTelemetry | `adapters/otel/` | ✅ Scaffold |
| RDF / Ontology / SHACL / SPARQL | `rdf/` | ✅ Full semantic layer |
| Knowledge Graph | `rdf/`, `llm_data_model/06_ontology/` | ✅ Ontology + graph model |
| RAG / Retrieval | `llm_data_model/07_retrieval/` | ✅ Strategy + patterns |

---

## Quick Start Paths

**"I want to understand the framework"** → Start with `GLOSSARY.md`, then `docs/02-core-concepts.md`

**"I want to see it run"** → `pip install -e .` then `coherence demo`

**"I want to see the data model"** → `llm_data_model/README.md` and `specs/`

**"I want to see the semantic layer"** → `rdf/README.md`

**"I want to see the architecture visually"** → `mermaid/README.md` (28 diagrams)

**"I want to query the system"** → `docs/18-iris.md` for IRIS interface documentation

**"I want to contribute"** → `CONTRIBUTING.md` and check the [roadmap](wiki/Roadmap.md)

---

*This map is updated as new features land. Last updated: 2026-02-15.*
