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

LinkedIn content primarily uses "Coherence Ops" and "Deep Sigma" language. This repository implements it as "Σ OVERWATCH" with a `core/` library.

---

## Concept → Code Map

### Core Framework

| LinkedIn Concept | Repo Location | Status |
|-----------------|---------------|--------|
| DLR (Decision Lineage Record) | `core/dlr.py` | ✅ Implemented + tested |
| RS (Reasoning Summary) | `core/rs.py` | ✅ Implemented + tested |
| DS (Drift Scan) | `core/ds.py` | ✅ Implemented + tested |
| MG (Memory Graph) | `core/mg.py` | ✅ Implemented + tested |
| Coherence Score | `core/scoring.py` | ✅ Implemented + tested |
| Drift → Patch loop | `tools/drift_to_patch.py` | ✅ Implemented |
| Seal / Sealing | `specs/episode.schema.json` | ✅ Schema + runtime |
| Claim–Evidence–Source chain | `rdf/ontology/`, `llm_data_model/` | ✅ Schema + ontology |
| Claim Primitive (atomic truth unit) | `specs/claim.schema.json`, `core/dlr.py` | ✅ Schema + runtime |
| Canon (blessed claim memory) | `specs/canon.schema.json` | ✅ Schema |
| Retcon (retroactive correction) | `specs/retcon.schema.json` | ✅ Schema |
| Claim-Native DLR | `specs/dlr.schema.json`, `core/dlr.py` | ✅ Schema + builder |
| Provenance | `rdf/queries/`, `core/mg.py` | ✅ Graph + SPARQL |
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
| PRIME (threshold gate) | `core/prime.py` | 🔜 Planned — Phase 1 |
| IRIS (operator interface) | `core/iris.py`, `specs/iris_query.schema.json`, `docs/18-iris.md` | ✅ Implemented — claim-graph queries |
| FranOPS (franchise operations mode) | `core/modes/franops.py` | ✅ Implemented — 12 handlers (canon lifecycle, retcon engine, inflation monitor) |
| IntelOps (intelligence operations mode) | `core/modes/intelops.py` | ✅ Implemented — 12 handlers (claim ingest→validate→drift→patch→MG update) |
| ReflectionOps (reflection operations mode) | `core/modes/reflectionops.py` | ✅ Implemented — 19 handlers (episodes, gates, severity, audit, killswitch + institutional memory) |
| AuthorityOps (authority operations mode) | `core/modes/authorityops.py` | ✅ Implemented — 19 handlers (action intake, actor/resource resolve, policy, DLR, assumptions, blast radius + simulation, decision gate, audit, delegation, drift detection) |
| ActionOps (action operations mode) | `core/modes/actionops.py` | ✅ Implemented — 19 handlers (commitment tracking + decision accounting) |
| Domain Mode Base | `core/modes/base.py` | ✅ Implemented — DomainMode + FunctionResult + deterministic replay |
| Cascade Engine | `core/modes/cascade.py` | ✅ Implemented — 27 cross-domain cascade rules with depth-limited propagation |
| Institutional Memory | `core/institutional_memory/` | ✅ Implemented — precedent registry, fingerprinting, consolidation, temporal decay |
| Drift Radar | `core/drift_radar/` | ✅ Implemented — cross-domain drift correlation, trending, forecasting, prioritization |
| Decision Accounting | `core/decision_accounting/` | ✅ Implemented — cost tracking, value scoring, debt engine, ROI computation |
| Event Contracts / Routing Table | `core/feeds/contracts/routing_table.json` | ✅ Implemented — 79 functions + 91 events with full contracts |
| Canon Workflow State Machine | `core/feeds/canon/workflow.py` | ✅ Implemented — PROPOSED→BLESSED→ACTIVE→SUPERSEDED/RETCONNED/EXPIRED |
| Episode State Machine | `core/episode_state.py` | ✅ Implemented — PENDING→ACTIVE→SEALED→ARCHIVED + FROZEN |
| Non-Coercion Audit Log | `core/audit_log.py` | ✅ Implemented — append-only, hash-chained NDJSON |
| Killswitch | `core/killswitch.py` | ✅ Implemented — freeze all episodes + halt proof |
| Severity Scorer | `core/severity.py` | ✅ Implemented — centralized drift severity computation |
| Money Demo (v2) | `enterprise/src/demos/money_demo/` | ✅ Implemented — 10-step end-to-end pipeline |
| CTI (Coherence Threat Index) | `core/scoring.py` (internal) | ⚡ Exists internally, being promoted to first-class |
| DAT (Dynamic Assertion Testing) | `tools/dat.py` | 🔜 Planned — Phase 4 |
| DDR (Deep Dive Review) | `tools/ddr.py` | 🔜 Planned — Phase 4 |
| ITCO (Integrated Truth & Coherence Ops) | — | 🔜 Planned — Phase 4 |
| Temperature regulation | `core/scoring.py` | 🔜 Planned — Phase 4 |
| Assumption TTL / Half-life | `specs/dte.schema.json` (TTL fields) | ✅ Schema-level |
| Prompt-to-Coherence Translator | `tools/prompt_translator.py` | 🔜 Planned — Phase 5 |
| Portfolio Management | `core/portfolio.py` | 🔜 Planned — Phase 5 |

### Narrative & Metaphors

| LinkedIn Concept | Repo Location | Notes |
|-----------------|---------------|-------|
| Stark Principle | `core/README.md` | Referenced in docs |
| Ferrari / Chassis | `GLOSSARY.md` | Positioning metaphor — see glossary |
| Iceberg Model | `GLOSSARY.md` | Enterprise AI stack model — see glossary |
| Binary-to-Diamond | `GLOSSARY.md` | Decision refinement model — see glossary |
| MU-TH-UR | `GLOSSARY.md` | Alien (1979) structural analogy — see glossary |
| Institutional Memory | `core/mg.py` | MG is the implementation of this concept |
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

**"I want to see the architecture visually"** → `docs/mermaid/README.md` (9 canonical diagrams + archive index)

**"I want to query the system"** → `docs/18-iris.md` for IRIS interface documentation

**"I want to contribute"** → `CONTRIBUTING.md` and check the [roadmap](wiki/Roadmap.md)

---

*This map is updated as new features land. Last updated: 2026-02-27.*
