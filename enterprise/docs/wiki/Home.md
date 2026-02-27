# DeepSigma Enterprise Wiki

**DeepSigma** is an execution-governance and coherence-operations platform for AI and human decision systems.
It applies pre-execution authority gates, policy-bound execution contracts, and sealed decision evidence to ensure governance is enforceable before state changes, then routes outcomes into the Drift → Patch learning loop.

> If you only read one thing: **governance must constrain execution, not just describe it afterward.**

---

## Start Here

| Page | Purpose |
|------|---------|
| [Wiki Index](Wiki-Index) | Canonical wiki structure and navigation |
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
| [Authority Boundary Primitive](Authority-Boundary-Primitive) | Pre-runtime governance declaration — what's allowed/denied/required before enforcement |

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

## FEEDS Event Surface

Event-driven pub/sub connecting governance primitives (TS, ALS, DLR, DS, CE) via file-based bus with manifest-first ingest, authority validation, triage state machine, and canon versioning.

| Stage | What it does |
|------|---------------|
| Event Envelope | 7 schemas, 6 golden fixtures, SHA-256 payload hashing, two-phase validation |
| File-Bus | Atomic publisher, poll subscriber, DLQ + replay, multi-worker safety |
| Ingest | Manifest-first, hash verification, atomic staging, PROCESS_GAP drift on failure |
| Consumers | Authority gate (DLR vs ALS), evidence completeness, SQLite triage store |
| Canon | Append-only store, claim validator, MG writer, supersedes chain |

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
| [ABP Schema](Authority-Boundary-Primitive) | Authority Boundary Primitive v1 |
| [Schemas](Schemas) | Full index of all JSON Schema specs |

---

## Integrations

| Integration | Page |
| --- | --- |
| SDK Packages | [SDK-Packages](SDK-Packages) |
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

## Latest Release + Telemetry

| Asset | Link |
|------|------|
| Latest release notes | [v2.0.6](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/release/RELEASE_NOTES_v2.0.6.md) |
| KPI composite radar | [release_kpis/radar_composite_latest.png](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/release_kpis/radar_composite_latest.png) |
| KPI delta table | [release_kpis/radar_composite_latest.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/release_kpis/radar_composite_latest.md) |
| TEC summary (C-TEC v1.0) | [release_kpis/TEC_SUMMARY.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/release_kpis/TEC_SUMMARY.md) |
| Mermaid canonical index | [docs/mermaid/README.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/README.md) |
| Mermaid archive index | [docs/archive/mermaid/ARCHIVE_INDEX.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/ARCHIVE_INDEX.md) |

---
## Repository Structure (`enterprise`)

```text
enterprise/
├─ artifacts/          # Sealed runs, templates, verifier bundles, authority ledger
├─ charts/             # Helm and deployment chart assets
├─ core_output/        # Core demo/runtime output pipeline stages
├─ dashboard/          # UI and dashboard services
├─ docker/             # Container build and runtime definitions
├─ docs/               # Enterprise documentation set
│  ├─ wiki/            # GitHub wiki source pages
│  ├─ mermaid/         # Canonical architecture/runtime diagrams
│  ├─ archive/         # Historical/archived design materials
│  ├─ release/         # Release notes and release documentation
│  ├─ examples/        # Demo and reference examples
│  └─ cookbook/        # Operational and integration recipes
├─ governance/         # Governance specs and operating artifacts
├─ ops/                # Monitoring/ops config (Grafana, Prometheus, etc.)
├─ pilot/              # Pilot data: assumptions, decisions, drift, patches, reports
├─ prompts/            # Prompt packs and prompt OS material
├─ release_kpis/       # KPI exports and telemetry summaries
├─ roadmap/            # Issue and milestone planning assets
├─ schemas/            # JSON Schema catalog (core + prompt_os + reconstruct)
├─ scripts/            # Tooling and automation scripts
├─ specs/              # Legacy/compatibility specs
├─ src/                # Enterprise Python packages and modules
└─ tests/              # Enterprise test suites and fixtures
```

Source of truth:
- Wiki source files: `enterprise/docs/wiki/*.md`
- Enterprise docs root: `enterprise/docs/`

---

## Reference

| Page | What it covers |
|------|---------------|
| [Glossary](Glossary) | All terms defined |
| [Roadmap](Roadmap) | Near-term and mid-term priorities |
| [Contributing](Contributing) | How to contribute |
