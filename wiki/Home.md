# Σ OVERWATCH / RAL — Wiki

**Σ OVERWATCH (RAL — Reality Await Layer)** is a runtime control plane for agentic AI.
It enforces deadlines, freshness, safe actions, and verification — then seals every decision into an immutable `DecisionEpisode` and feeds the Drift → Patch learning loop.

> If you only read one thing: **RAL is "await for reality."**

---

## Start Here

| Page | Purpose |
|------|---------|
| [Quickstart](Quickstart) | Get a supervised agent running in minutes |
| [Concepts](Concepts) | The four problems RAL solves and the primitives that solve them |
| [Architecture](Architecture) | System diagram and component map |
| [FAQ](FAQ) | Common questions |

---

## Core Runtime

The runtime enforces four contracts on every decision before it is sealed.

| Page | What it covers |
|------|---------------|
| [Contracts](Contracts) | All four contract types: DTE, Freshness, Action, Verification |
| [DTE Schema](DTE-Schema) | Time budgets, stage limits, degrade triggers |
| [Action Contract Schema](Action-Contract-Schema) | Blast radius, idempotency, rollback, authorization modes |
| [Degrade Ladder](Degrade-Ladder) | Six rungs from `warn` → `block`; how the supervisor degrades under pressure |
| [Verifiers](Verifiers) | Postcondition checks (`read_after_write`, `invariant_check`, custom) |
| [Sealing & Episodes](Sealing-and-Episodes) | Immutable `DecisionEpisode` envelope + SHA-256 seal |
| [Runtime Flow](Runtime-Flow) | Step-by-step request lifecycle |
| [Policy Packs](Policy-Packs) | Versioned bundles of DTE + Action constraints |

---

## Drift & Governance

| Page | What it covers |
|------|---------------|
| [Drift → Patch](Drift-to-Patch) | How drift signals become structured Patch Packets |
| [Drift Schema](Drift-Schema) | 10 drift types, 3 severity levels, fingerprint dedup |
| [Coherence Ops Mapping](Coherence-Ops-Mapping) | DLR / RS / DS / MG — the four governance artifacts |
| [IRIS](IRIS) | Operator query engine: WHY / WHAT\_CHANGED / WHAT\_DRIFTED / RECALL / STATUS |
| [Unified Atomic Claims](Unified-Atomic-Claims) | Claim primitive — the unit of institutional memory |
| [Canon](Canon) | Blessed claim memory and canon entry lifecycle |
| [Retcon](Retcon) | Retroactive claim correction with full audit trail |
| [LLM Data Model](LLM-Data-Model) | How LLM interactions map to the governance schema |

---

## Excel-First Governance (v0.6.2)

| Page | What it covers |
|------|---------------|
| [Creative Director Suite](Creative-Director-Suite) | Dataset, workbook template, generator, quickstart |
| [Excel-First Governance](Excel-First-Governance) | BOOT protocol, 7 table schemas, 6-lens prompting, writeback contract |

---

## Exhaust Inbox

Captures AI interaction exhaust (prompts, completions, tool calls, metrics) and routes it into the governance pipeline automatically.

| Page | What it covers |
|------|---------------|
| [Exhaust Inbox](Exhaust-Inbox) | Full feature docs: adapters, API, LLM extraction, coherence scoring |

**Adapters:** LangChain · Anthropic direct · Azure OpenAI batch
**API:** 10 REST endpoints — ingest → assemble → refine → commit
**LLM extraction:** `EXHAUST_USE_LLM=1` enables Anthropic-backed bucket extraction with rule-based fallback

---

## Schemas

| Schema | Description |
|--------|-------------|
| [Episode Schema](Episode-Schema) | Sealed `DecisionEpisode` — the core output |
| [DTE Schema](DTE-Schema) | Decision Timing Envelope |
| [Action Contract Schema](Action-Contract-Schema) | Safe action constraints |
| [Drift Schema](Drift-Schema) | Drift signal structure |
| [Policy Pack Schema](Policy-Pack-Schema) | Policy bundle format |
| [Claim Schema](Unified-Atomic-Claims) | Unified Atomic Claim |
| [Canon Schema](Canon) | Canon entry format |
| [Retcon Schema](Retcon) | Retroactive correction record |
| [Schemas](Schemas) | Full index of all JSON Schema specs |

---

## Integrations

| Integration | Page |
|------------|------|
| MCP (Model Context Protocol) | [MCP](MCP) |
| LangChain | [LangChain](LangChain) |
| Palantir Foundry | [Palantir-Foundry](Palantir-Foundry) |
| Microsoft Power Platform | [Power-Platform](Power-Platform) |
| OpenTelemetry | [OpenTelemetry](OpenTelemetry) |

---

## Operations

| Page | What it covers |
|------|---------------|
| [Operations](Operations) | Deployment, configuration, environment variables |
| [SLOs & Metrics](SLOs-and-Metrics) | Latency, drift rate, verification pass rate targets |
| [Replay & Testing](Replay-and-Testing) | Episode replay harness and test fixtures |
| [Security](Security) | Threat model, seal integrity, authorization |

---

## Reference

| Page | What it covers |
|------|---------------|
| [Glossary](Glossary) | All terms defined |
| [Roadmap](Roadmap) | Near-term and mid-term priorities |
| [Contributing](Contributing) | How to contribute |
