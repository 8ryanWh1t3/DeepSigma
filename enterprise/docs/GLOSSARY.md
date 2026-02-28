# Deep Sigma — Glossary

Canonical definitions for all concepts across the Deep Sigma ecosystem.
Organized by layer — from brand identity through runtime architecture to operational modes.

---

## Brand & Identity

| Term | Definition |
|------|-----------|
| **Deep Sigma** | The umbrella brand and research program. Encompasses the full body of work: frameworks, tools, content, and operational philosophy. "Ideas spark. Persistence builds. Deep Sigma delivers." |
| **Coherence Ops** | The operational framework for organizational coherence management. Defines how truth, reasoning, and memory are governed across decisions. The methodology. |
| **Σ OVERWATCH** | The runtime engine and control plane that enforces Coherence Ops contracts. Makes agentic automation production-safe through DTE, action contracts, verification, and sealed episodes. The software. |
| **Language-Native Modeling Dynamics** | The theoretical foundation: how complex systems absorb incompleteness and failure as design features rather than collapsing under contradictions. Bridges Gödel's incompleteness theorem, organizational theory, and AI systems design. |

---

## Core Framework — Truth, Reasoning, Memory

| Term | Definition |
|------|-----------|
| **Truth–Reasoning–Memory** | The three invariants that govern every decision in Coherence Ops. Truth = claim + evidence + source. Reasoning = facts vs interpretation + assumptions with expiry + rejected options with rationale. Memory = seal + version + patch (no overwrite, only evolution). |
| **PRIME** | The governance threshold gate. Sits atop DLR/RS/DS/MG and converts LLM probability gradients into decision-grade actions using Truth–Reasoning–Memory invariants. "LLM proposes. PRIME disposes." |
| **IRIS** | The operator-facing interface layer. Provides query resolution for "why did we decide X?" and "what's drifting?" with sub-60-second response targets. The terminal through which operators interact with PRIME. |
| **Claim–Evidence–Source** | The truth chain: every assertion must link to evidence, which must link to a source with provenance. No claim ships without this chain. |

---

## Unified Atomic Claims (v0.2.0)

| Term | Definition |
|------|-----------|
| **AtomicClaim** | The universal primitive for all assertions in Coherence Ops. Contains: claimId, statement, truthType, evidence chain, confidence score, half-life, graph topology (dependsOn, contradicts, supersedes, supports), and a cryptographic seal. Every decision, observation, or conclusion is modelled as an AtomicClaim. |
| **Claim Primitive** | The JSON Schema specification (`specs/claim.schema.json`) defining the AtomicClaim structure. Draft 2020-12, `additionalProperties: false`. |
| **Claim-Native DLR** | A Decision Lineage Record that uses AtomicClaims as first-class citizens rather than opaque text fields. Each DLR entry carries typed claim references with roles (supporting, primary, dissenting, rejected) and a rationale graph of edges between claims. |
| **Canon** | A "blessed" claim that has been validated, reviewed, and graduated to institutional memory. Governed by `specs/canon.schema.json`. Canon claims have a promotion chain showing who blessed them and when. |
| **Retcon** | A retroactive correction to a claim. Instead of overwriting, Coherence Ops creates a retcon record linking the corrected claim to its replacement with a full audit trail. Governed by `specs/retcon.schema.json`. |
| **Status Light** | Derived health indicator for a claim: ✅ GREEN (confidence ≥ 0.7, not expired, sealed), ⚠️ YELLOW (confidence 0.4–0.7, or nearing half-life), 🔴 RED (confidence < 0.4, expired, or unsealed). |
| **Half-Life** | Every claim has a temporal decay parameter. When the half-life expires, the claim’s confidence degrades and the status light shifts toward YELLOW/RED. Enforces the principle: no assertion lives forever without re-validation. |
| **Claim Graph Topology** | The web of relationships between claims: `dependsOn` (prerequisite), `contradicts` (opposing), `supersedes` (replaces), `supports` (reinforces). Stored as edges in the MemoryGraph and traversed by IRIS for provenance queries. |
| **ClaimNativeDLRBuilder** | Python class in `core/dlr.py` that constructs claim-native DLR entries from sealed episodes and their associated claims. |

---

## The Four Pillars (Coherence Ops Artifacts)

| Term | Abbreviation | Definition |
|------|-------------|-----------|
| **Decision Lineage Record** | DLR | The truth constitution for a decision class. Captures the DTE reference, action contract, verification requirement, and policy pack stamp from a sealed DecisionEpisode. Answers: "what policy governed this decision, and was it followed?" |
| **Reasoning Summary** | RS | Aggregates sealed episodes into learning summaries: outcome distribution, degradation frequency, verification pass rates, notable divergences, and human-readable takeaways. Answers: "what happened, what degraded, what should we learn?" |
| **Drift Scan** | DS | Collects and structures runtime drift signals by type, severity, fingerprint, and recurrence. Feeds the audit loop and scoring engine. Answers: "what is breaking, how often, and how badly?" |
| **Memory Graph** | MG | Provenance and recall graph storing nodes (episodes, actions, drift fingerprints, patches) and edges (provenance, causation, recurrence). Enables sub-60-second "why did we do this?" retrieval. Answers: "what happened before, why, and what changed as a result?" |

---

## Runtime Architecture (Σ OVERWATCH)

| Term | Abbreviation | Definition |
|------|-------------|-----------|
| **AL6 (Agentic Liability 6)** | AL6 | The six dimensions of agentic reliability: (1) Deadline — decision window, (2) Distance — hops/fan-out, (3) Data Freshness — TTL/snapshot age, (4) Variability — P95/P99 + jitter, (5) Drag — queue/lock/IO contention, (6) Degrade — fallback/bypass/abstain. |
| **Decision Timing Envelope** | DTE | Per-decision contract specifying deadlines, stage budgets, TTL freshness gates, degrade ladders, and safety/verification thresholds. The primary governance contract. |
| **Degrade Ladder** | — | Ordered fallback sequence when a decision cannot meet its DTE: degrade quality → use cache → fallback to heuristic → abstain. Each step has blast radius and rationale. |
| **Action Contract** | — | Required envelope for state-changing actions: blast radius tier, idempotency key, rollback plan, authorization mode (auto / human-in-the-loop / blocked). |
| **DecisionEpisode** | — | The sealed unit of audit: truth used → reasoning applied → action taken → verification result → outcome observed. Immutable once sealed. |
| **DriftEvent** | — | Structured failure/variance signal: time drift, freshness drift, fallback, bypass, verify failure, outcome divergence, fanout, contention. Triggers the patch workflow. |
| **Drift-to-Patch** | — | The operational loop: detect drift → fingerprint → match pattern → generate patch proposal → apply → re-score. Continuous coherence repair. |
| **Seal / Sealing** | — | Making a record immutable and tamper-evident. Sealed records are versioned; edits create new versions, never overwrite. |

---

## Measurement & Assessment

| Term | Abbreviation | Definition |
|------|-------------|-----------|
| **Coherence Threat Index** | CTI | Composite metric measuring coherence risk across all four pillars. Dimensions: policy adherence (DLR), outcome health (RS), drift control (DS), memory completeness (MG). Green/yellow/red severity. |
| **Dynamic Assertion Testing** | DAT | Test runner for coherence assertions: takes a set of claims about system state, runs them against current coherence data, reports which assertions hold and which have drifted. A coherence test suite. |
| **Deep Dive Review** | DDR | Comprehensive review of a specific decision class or drift pattern, pulling from all four pillars to produce a structured analysis with recommendations. |
| **Integrated Truth and Coherence Operations** | ITCO | Composite assessment pipeline: DAT → CTI scoring → DDR when thresholds breach. The full coherence health check. |
| **Coherence Score** | — | Unified 0–100 score computed from all four artifact layers. Per-dimension breakdown plus composite. |
| **Temperature** | — | System-level coherence heat metric. Temperature rises when drift accumulates and unresolved signals stack; cools when patches resolve drift and scores improve. Sustained high temperature triggers degrade ladder escalation. |
| **Assumption TTL / Half-life** | — | Every assumption has a time-to-live. When expired, assumptions must be re-validated or the decisions built on them are flagged for drift scan. No silent expiry. |

---

## Operational Modes

| Term | Definition |
|------|-----------|
| **FranOPS** | Franchise Operations mode. 12 function handlers (FRAN-F01–F12): canon propose/bless/enforce, retcon assess/execute/propagate, inflation monitor, expire, supersede, scope check, drift detect, rollback. Canon workflow state machine: PROPOSED → BLESSED → ACTIVE → UNDER_REVIEW → SUPERSEDED/RETCONNED/EXPIRED. Implementation: `core/modes/franops.py`. |
| **IntelOps** | Intelligence Operations mode. 12 function handlers (INTEL-F01–F12): claim ingest, validate, drift detect, patch recommend, MG update, canon promote, authority check, evidence verify, triage, supersede, half-life check, confidence recalc. Implementation: `core/modes/intelops.py`. |
| **ReflectionOps** | Reflection Operations mode. 12 function handlers (RE-F01–F12): episode begin/seal/archive, gate evaluate/degrade/killswitch, non-coercion audit, severity scoring, coherence check, reflection ingest, IRIS resolve, episode replay. Implementation: `core/modes/reflectionops.py`. |
| **DomainMode** | Base class for all domain modes. Provides `handle(function_id, event, context) → FunctionResult` dispatch and `replay()` for deterministic verification. Implementation: `core/modes/base.py`. |
| **FunctionResult** | Return type from every domain mode handler. Contains: `function_id`, `success`, `events_emitted`, `drift_signals`, `mg_updates`, `elapsed_ms`, `replay_hash` (SHA-256 of deterministic output). |
| **Cascade Engine** | Cross-domain event propagation engine with 7 declarative rules. When an event in one domain triggers a rule, the cascade engine invokes the target domain's handler with depth limiting to prevent infinite loops. Implementation: `core/modes/cascade.py`. |
| **Event Contracts** | Declarative routing table mapping 36 functions + 39 events to FEEDS topics, subtypes, handler paths, required payload fields, and emitted events. Validated at publish time. Implementation: `core/feeds/contracts/routing_table.json`. |
| **Canon Workflow** | State machine governing canon entry lifecycle: PROPOSED → BLESSED → ACTIVE → UNDER_REVIEW → SUPERSEDED/RETCONNED/EXPIRED. Also REJECTED and FROZEN states. Transition validation prevents illegal state changes. Implementation: `core/feeds/canon/workflow.py`. |
| **Episode State Machine** | State machine governing episode lifecycle: PENDING → ACTIVE → SEALED → ARCHIVED. Supports FROZEN state for killswitch scenarios. `freeze_all()` halts all active episodes. Implementation: `core/episode_state.py`. |
| **Non-Coercion Audit Log** | Append-only, hash-chained NDJSON audit log for domain mode actions. Each entry chains to the previous via SHA-256 hash. `verify_chain()` detects tampering. Implementation: `core/audit_log.py`. |
| **Killswitch** | Emergency halt mechanism: freezes all ACTIVE episodes, emits sealed halt proof with authorization details, logs to audit trail. Requires explicit authority check to resume. Implementation: `core/killswitch.py`. |
| **Severity Scorer** | Centralized drift severity computation using drift-type weights, multi-signal aggregation, and GREEN/YELLOW/RED classification. All domains call this for consistent severity assessment. Implementation: `core/severity.py`. |
| **Retcon Executor** | Retcon assessment (impact analysis, dependent claim enumeration) and execution (supersede chain, audit trail, drift signal emission). Called by FranOps FRAN-F04 and FRAN-F05. Implementation: `core/feeds/canon/retcon_executor.py`. |
| **Inflation Monitor** | Per-domain canon health monitoring with four threshold types: claim count > 50, contradiction density > 10%, avg claim age > 30 days, supersedes depth > 5. Breaches emit `canon_inflation` drift signal. Implementation: `core/feeds/canon/inflation_monitor.py`. |

---

## Integrations & Adapters

| Term | Definition |
|------|-----------|
| **MCP** | Model Context Protocol. JSON-RPC stdio transport exposing OVERWATCH primitives as MCP tools for LLM agent integration. |
| **OpenClaw** | Integration adapter for the OpenClaw skill runner framework: Skill Runner → Action Contract → Verify → Seal. |
| **OpenTelemetry / OTel** | Telemetry export hooks for OVERWATCH runtime metrics. Plugs into standard observability stacks. |
| **RDF / Ontology** | Semantic layer: OWL ontology (Core 8 classes), SHACL validation shapes, SPARQL executive queries, SharePoint-to-RDF mappings. Triples > spreadsheets. |
| **Policy Packs** | Versioned enforcement bundles: a policy pack declares thresholds, required verifications, allowed degrade steps, and forbidden actions. Stamped onto every sealed episode. Hash-verified for integrity. |

---

## Narrative Frameworks & Metaphors

| Term | Definition |
|------|-----------|
| **Stark Principle** | "Don't buy the tip. Build the chassis." Reject surface-level AI (copilots, chat interfaces) without the structural stack underneath (context engineering, data contracts, provenance, decision memory, integration). |
| **Ferrari / Chassis Metaphor** | AI is the Ferrari engine. Coherence Ops is the chassis + brakes + telemetry + black box recorder. Without structure, speed amplifies drift. With structure, speed amplifies decision dominance. |
| **Iceberg Model** | Most enterprise AI investment goes "above water" (copilots, chat, UX). Real value is "below water" (context engineering, data contracts, identity/access, provenance, decision memory, integration debt, tribal knowledge). |
| **Binary-to-Diamond Model** | Most decisions are forced into binary (yes/no) because humans had to compress reality. LLMs reveal the hidden dimensions (the gradient). PRIME cuts the edges (thresholds). Coherence Ops keeps the diamond true over time. |
| **MU-TH-UR** | Reference to the AI system in Alien (1979): institutional authority encoded in silicon. Had truth authority, directive continuity, total mission memory, and execution reach. The crew had context fragments; MU-TH-UR had institutional coherence. We are now building this intentionally. |
| **Institutional Memory** | The organizational capability to recall, with lineage, why decisions were made. "60 seconds or it doesn't exist." The operational promise of the Memory Graph. |
| **Prompt-to-Coherence Translator** | The methodology for compiling natural language prompts into Coherence Ops primitives: types (data model), policies (invariants), events (state machine), renderers (output schema). Prompt engineering becomes Coherence Engineering. |
| **Signal Over Noise** | Design principle: every output should increase the signal-to-noise ratio. If it doesn't clarify, it obscures. Clarity proves competence; confusion signals weakness. |
| **42** | Recurring motif. The answer to life, the universe, and everything. In Coherence Ops: the reminder that having the answer is meaningless without the right question, the right framing, and the memory of why you asked. |

---

## Infrastructure & Tooling

| Term | Definition |
|------|-----------|
| **Supervisor / run_supervised** | CLI tool that orchestrates a full decision cycle: receive context → evaluate DTE → select degrade step → execute action → verify → seal episode. |
| **Replay Harness** | Deterministic replay tool: takes sealed episodes and re-executes them through the pipeline to validate behavior, test patches, and verify coherence improvements. |
| **Verifiers** | Verification library: read-after-write checks (verify action produced expected state change) and invariant checks (verify system-level constraints hold). |
| **Reconciler** | Cross-artifact consistency engine: detects when DLR, RS, DS, and MG disagree and produces reconciliation proposals with blast radius assessment. |
| **Coherence Auditor** | Periodic health check across all four artifact layers. Detects orphaned records, stale references, unresolved drift, and coverage gaps. |

---

*See also: [Language Map](docs/01-language-map.md) for a full mapping of LinkedIn content concepts to repository artifacts.*
