---
title: "ABOUT — Reality Await Layer (RAL)"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-17"
spec_id: "ABOUT-RAL-001"
---

<div align="center">

# Reality Await Layer (RAL)

**The control plane for agentic AI that refuses to let agents outrun reality.**

*Deadlines · Freshness · Contracts · Verification · Sealed Episodes · Drift→Patch*

[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP Ready](https://img.shields.io/badge/MCP-Ready-blueviolet.svg)](./adapters/mcp/)
[![Coherence Ops](https://img.shields.io/badge/Coherence_Ops-Compatible-green.svg)](./coherence_ops/)

</div>

---

## What Is a Reality Await Layer?

Agents are fast. Reality is slow. The gap between them is where failures compound.

An LLM agent can chain twelve tool calls in under a second. It can fan out across
APIs, write to databases, and trigger downstream workflows — all before a human
blinks. But speed without structure is not velocity; it is drift at scale.

The **Reality Await Layer** is the infrastructure that sits between an agent's
intent and the world's state. It enforces a simple contract: before you act,
prove your inputs are fresh; before you commit, verify the outcome; after you
finish, seal the record so the institution can learn from it.

RAL does not slow agents down. It makes their speed trustworthy.

---

## The Problem RAL Solves

Every agentic system faces the same failure modes, and most discover them in
production:

**Stale inputs** — the agent decides based on data that changed between read and
act. A price moved, a seat filled, a policy updated. The decision was correct
for a world that no longer exists. This is the TOCTOU (time-of-check /
time-of-use) problem applied to AI.

**Invisible blast radius** — a state-changing action that seems local cascades
through dependencies the agent cannot see. No rollback plan. No idempotency
guarantee. No blast-radius declaration.

**Unauditable decisions** — the agent acted, the system changed, and nobody can
reconstruct *why* — what evidence was used, what alternatives were considered,
what thresholds applied. When the regulator asks, the answer is a log file and
a shrug.

**Silent drift** — assumptions that were true at deployment slowly decay. TTLs
expire. Policies update. Data sources shift schema. The system continues to
operate, confidently wrong, until an incident forces discovery.

**No institutional memory** — every agent invocation starts from zero. The
organization learns nothing from its own decisions. The same mistakes recur
because there is no feedback loop from outcome back to policy.

RAL addresses all five by treating every agent decision as a structured episode
with enforceable contracts at every phase boundary.

---

## How RAL Works

Every decision passes through five gates. No gate can be skipped. Each gate
produces an artifact that becomes part of the institution's permanent memory.

### Gate 1 — Decision Timing Envelope (DTE)

Before the agent begins, RAL binds a contract to the decision:

```
deadline:        2026-02-17T16:30:00Z      # hard wall — decision must close
stage_budgets:   context: 2s | plan: 3s | act: 5s | verify: 2s
freshness_ttl:   price_feed: 30s | inventory: 60s | policy: 3600s
degrade_ladder:  cache_bundle → small_model → rules_only → hitl → abstain
hop_limit:       4
fan_out_limit:   8
```

If the deadline passes, the DTE forces a degrade step — not a crash, not an
uncontrolled retry, but a structured fallback with recorded rationale. The
degrade ladder is ordered by blast radius: prefer less damage over more
ambition.

### Gate 2 — Freshness & TTL Enforcement

Every input claim carries metadata: `capturedAt`, `halfLife`, `confidence`,
`statusLight`. RAL checks freshness at the moment of use, not at the moment
of fetch.

A claim captured 45 seconds ago with a 30-second TTL is **stale**. RAL will not
let the agent use it without triggering the degrade ladder. This eliminates the
TOCTOU class of failures: the system refuses to act on a world-state it cannot
confirm is current.

Claims are modeled as `AtomicClaim` primitives with typed evidence chains,
confidence scores (0.0–1.0), truth types (empirical, derived, asserted, policy,
inferred), and graph topology (dependsOn, contradicts, supersedes, supports).

### Gate 3 — Safe Action Contract

Before any state-changing action executes, it must be wrapped in a contract:

```
blast_radius:    tier-2 (cross-service)
idempotency_key: act-7f3a-2026-02-17-001
rollback_plan:   revert inventory reservation via API
auth_mode:       auto              # auto | hitl | blocked
```

Actions above a configurable blast-radius tier require human-in-the-loop
approval. Actions without rollback plans at tier-2+ are blocked. This is not
a suggestion — it is an enforcement boundary.

### Gate 4 — Verification

After the action executes, RAL performs read-after-write verification: did the
action produce the expected state change? Verification is not optional. A
decision episode without verification is incomplete and will be flagged by the
coherence auditor.

Verification types include state-change confirmation, invariant checks, and
cross-artifact consistency validation.

### Gate 5 — Seal & Memory

The completed decision — inputs, reasoning, action, verification, outcome — is
sealed into an immutable `DecisionEpisode`:

```
seal_hash:   SHA-256 of episode content
sealed_at:   2026-02-17T16:25:03Z
version:     1
status:      sealed
```

Sealed episodes are **append-only**. Edits produce new versions with patch logs.
The Memory Graph (MG) absorbs the episode as a node and links it via typed
provenance edges to related episodes, actions, drift signals, and patches.

Any operator can now answer "why did we do this?" in under 60 seconds via the
IRIS query engine.

---

## The Drift → Patch Loop

Sealing is not the end. RAL continuously monitors sealed episodes against
current reality:

```
DECIDE ──→ SEAL ──→ MONITOR ──→ DRIFT? ──→ PATCH ──→ MEMORY
  │                                                      │
  └────────────────────── loop ──────────────────────────┘
```

**Drift types** are structured and enumerated: time drift (deadline miss),
freshness drift (TTL expiry), fallback drift (degrade ladder activation),
bypass drift (gate skip), verification drift (verify failure), outcome drift
(result divergence), fanout drift (hop/fan-out limit breach), and contention
drift (lock/queue/IO pressure).

When drift is detected, RAL fingerprints it, matches it against known patterns,
generates a patch proposal, applies the correction, and re-scores coherence.
The patch itself becomes a sealed record in the Memory Graph, closing the
feedback loop.

**Without this loop:** drift accumulates silently. Mean time to detect a stale
assumption: months, or an incident.

**With this loop:** drift is caught at deviation. Remediation is a patch, not a
crisis. Memory strengthens with every correction.

---

## Coherence Ops Compatibility

RAL is the runtime enforcement engine for **Coherence Ops** — the operational
framework that governs truth, reasoning, and memory across institutional
decisions.

Coherence Ops materializes through four canonical artifacts:

| Artifact | Role | RAL Integration |
|----------|------|-----------------|
| **DLR** (Decision Ledger Record) | Truth receipt — policy, claims, verification | Produced at Gate 5 from sealed episodes |
| **RS** (Reasoning Summary) | Learning journal — outcomes, degradations, lessons | Aggregated from episode batches |
| **DS** (Drift Signal) | Alarm — what is breaking, how badly, how to fix | Emitted by the Drift→Patch loop |
| **MG** (Memory Graph) | Institutional brain — provenance graph of all decisions | Absorbs every sealed episode and patch |

RAL produces the raw material (sealed episodes, drift events, patches).
Coherence Ops transforms that material into institutional memory through
scoring, auditing, and reflection workflows.

The **Coherence Score** (0–100, A–F) measures health across all four pillars.
The **Coherence Threat Index** (CTI) tracks risk accumulation. When temperature
rises — when drift accumulates faster than patches resolve it — the system
escalates through the degrade ladder automatically.

---

## AL6: Six Dimensions of Agentic Reliability

RAL measures every decision across six dimensions — the **Agentic Liability 6
(AL6)** framework:

| # | Dimension | What It Measures |
|---|-----------|------------------|
| 1 | **Deadline** | Did the decision close within its timing envelope? |
| 2 | **Distance** | How many hops, fan-outs, and tool calls were required? |
| 3 | **Data Freshness** | Were all input claims within their TTL at time of use? |
| 4 | **Variability** | What was the P95/P99 latency and jitter? |
| 5 | **Drag** | How much queue, lock, and IO contention was encountered? |
| 6 | **Degrade** | Did the system fall back, bypass, or abstain? |

Every sealed episode carries its AL6 vector. Coherence scoring weights these
dimensions to produce the composite health score. Operators can filter, sort,
and alert on any dimension independently.

---

## MCP Integration

RAL exposes its primitives as **Model Context Protocol (MCP)** tools via
JSON-RPC over stdio transport. Any MCP-compatible agent framework can call
RAL natively:

```
Tools exposed via MCP:
  overwatch.dte.create       # Bind a Decision Timing Envelope
  overwatch.claim.validate   # Check claim freshness and confidence
  overwatch.action.contract  # Register a Safe Action Contract
  overwatch.verify.check     # Read-after-write verification
  overwatch.episode.seal     # Seal and commit a DecisionEpisode
  overwatch.drift.scan       # Query current drift signals
  overwatch.iris.query       # WHY / WHAT_CHANGED / WHAT_DRIFTED / RECALL / STATUS
```

Additional adapters exist for **OpenClaw** (skill runner integration) and
**OpenTelemetry** (telemetry export to standard observability stacks).

---

## IRIS: The Operator Interface

IRIS is the query engine that makes the Memory Graph actionable. It answers
five question types in under 60 seconds:

| Query Type | Question | Example |
|------------|----------|---------|
| **WHY** | Why was this decision made? | "Why did agent-4 choose vendor B?" |
| **WHAT_CHANGED** | What changed since this decision? | "What changed since ep-042 was sealed?" |
| **WHAT_DRIFTED** | What assumptions have decayed? | "Which TTLs expired in the last hour?" |
| **RECALL** | What happened before in this category? | "Show all tier-3 blast-radius actions" |
| **STATUS** | What is the current system health? | "Current coherence score and temperature" |

IRIS traverses the Memory Graph's provenance edges to reconstruct the full
decision lineage: what claims were used, what policy applied, what alternatives
were rejected, what verification confirmed, and what patches have since
modified the outcome.

---

## Quick Start

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt

# Score coherence (0–100, A–F)
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Full pipeline: episodes → DLR → RS → DS → MG → report
python -m coherence_ops.examples.e2e_seal_to_report

# Drift → Patch cycle
python -m coherence_ops.examples.drift_patch_cycle
# BASELINE 90.00 (A) → DRIFT 85.75 (B) → PATCH 90.00 (A)

# Query the Memory Graph
python -m coherence_ops iris query --type WHY --target ep-001
```

Full walkthrough: [HERO_DEMO.md](HERO_DEMO.md)

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Framework                       │
│            (LangGraph / LangChain / Custom)              │
└──────────────────────┬──────────────────────────────────┘
                       │  MCP / JSON-RPC
┌──────────────────────▼──────────────────────────────────┐
│              Σ OVERWATCH — Reality Await Layer           │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐  │
│  │   DTE   │→ │ Freshness│→ │ Action │→ │  Verify   │  │
│  │ Binding │  │   Gate   │  │Contract│  │           │  │
│  └─────────┘  └──────────┘  └────────┘  └─────┬─────┘  │
│                                               │         │
│  ┌────────────────────────────────────────────▼──────┐  │
│  │              Seal → DecisionEpisode               │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                              │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │         Drift Monitor → Patch → Memory            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌──────────┐     │
│  │ DLR │  │ RS  │  │ DS  │  │ MG  │  │   IRIS   │     │
│  └─────┘  └─────┘  └─────┘  └─────┘  └──────────┘     │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Your Infrastructure                    │
│         (Databases / APIs / Services / Users)            │
└─────────────────────────────────────────────────────────┘
```

RAL sits between the agent and the world. It does not replace agent frameworks,
data platforms, or workflow engines. It governs the boundary where autonomous
intent meets mutable reality.

---

## Project Map

| Directory | Purpose |
|-----------|---------|
| `canonical/` | Normative specs: DLR, RS, DS, MG, Prime Constitution |
| `coherence_ops/` | Python library + CLI + examples |
| `adapters/` | MCP, OpenClaw, OpenTelemetry integrations |
| `specs/` | JSON Schemas (11 schemas including Claim, Canon, Retcon) |
| `dashboard/` | React 18 + TypeScript real-time monitoring dashboard |
| `engine/` | Compression, degrade ladder, supervisor runtime |
| `verifiers/` | Read-after-write and invariant verification library |
| `llm_data_model/` | LLM-optimized canonical data model |
| `ontology/` | OWL ontology, SHACL shapes, SPARQL queries |
| `policy_packs/` | Versioned enforcement bundles |
| `docs/` | Extended documentation (20+ docs) |
| `mermaid/` | 28+ architecture and flow diagrams |

---

## Design Principles

**No silent failures.** Every gate produces an artifact or raises a structured
signal. Errors are not suppressed; they are drift events with severity,
fingerprint, and patch guidance.

**Append-only memory.** Sealed records are immutable. Changes produce new
versions. The institution's decision history is a monotonically growing graph,
never a mutable log.

**Degrade over crash.** When the ideal path is unavailable — stale data,
timeout, unsafe action — the system follows the degrade ladder rather than
failing uncontrollably. Every degrade step is recorded with its rationale.

**Speed is not the bottleneck.** RAL is designed to add sub-second overhead to
agent decisions. The freshness check, action contract validation, and seal
operation are lightweight. The cost of not having them is measured in incidents,
not milliseconds.

**Framework-agnostic.** RAL does not require a specific agent framework. It
exposes MCP tools, REST endpoints, and Python APIs. If your agent can make a
function call, it can use RAL.

---

## See Also

| Resource | Path |
|----------|------|
| Front door | [START_HERE.md](START_HERE.md) |
| 5-min walkthrough | [HERO_DEMO.md](HERO_DEMO.md) |
| Prime Constitution | [canonical/prime_constitution.md](canonical/prime_constitution.md) |
| Full glossary | [GLOSSARY.md](GLOSSARY.md) |
| Core concepts | [docs/02-core-concepts.md](docs/02-core-concepts.md) |
| IRIS documentation | [docs/18-iris.md](docs/18-iris.md) |
| MCP adapter | [adapters/mcp/](adapters/mcp/) |
| Dashboard | [dashboard/](dashboard/) |
| Navigation index | [NAV.md](NAV.md) |

---

<div align="center">

**Σ OVERWATCH**

*Agents propose. Reality disposes. RAL makes sure you remember why.*

</div>
