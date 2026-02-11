# Coherence Ops Integration: Σ OVERWATCH / RAL + LLM Data Model

Σ OVERWATCH (a.k.a. **RAL — Reality Await Layer**) is an **optional execution add-on** to Coherence Ops.
It governs agentic runtime behavior (deadlines, freshness, safe actions, verification) and emits **sealed DecisionEpisodes** plus **Drift→Patch** signals.

This document shows how the exhaust maps into Coherence Ops canonical artifacts (**DLR / RS / DS / MG**) and how the **LLM Data Model** must carry timestamps + TTL + provenance to make RAL possible.

---

## 1) Where RAL sits (no disruption to core)

**Coherence Ops (core)** defines *Truth · Reasoning · Memory* and the 4 canonical artifacts.
**RAL (optional)** enforces those invariants **at runtime** and produces the exhaust automatically.

```text
Agent Frameworks (LangChain/LangGraph/etc)
          |
          v
   ┌───────────────────────────────┐
   │  RAL / Σ OVERWATCH (Control)   │
   │  - DTE deadlines & budgets     │
   │  - TTL / TOCTOU freshness      │
   │  - Safe Action Contract        │
   │  - Verification                │
   │  - Sealing + Drift→Patch       │
   └───────────────────────────────┘
          |
          v
Data / Action Planes (Foundry, APIs, Power Platform, etc)
```

---

## 2) Canonical mapping: Truth · Reasoning · Memory

### Truth
What was true **at decision time** (and how fresh it was):
- `capturedAt` timestamps on features/tool outputs
- `ttlMs`, `maxFeatureAgeMs`, `ttlBreachesCount`
- `evidenceRefs` / `sourceRef` provenance

### Reasoning
Why the system chose to act / abstain / bypass:
- plan summary + constraints
- degrade step chosen (cache_bundle → small_model → rules_only → hitl → abstain/bypass)
- verification requirement threshold and results

### Memory
The immutable unit of recall:
- **Sealed DecisionEpisode** (`sealHash`, `sealedAt`)

---

## 3) Artifact mapping: DLR / RS / DS / MG

### DLR (Decision Log Record) — Truth constitution for an episode
RAL provides:
- **DTE** reference (decisionType/version)
- **Action Contract** used (or blocked)
- **Verification requirement** + method

DLR becomes the stable "policy of action" for that decision class.

### RS (Reflection Session) — judgment + outcomes + learning
RAL provides:
- outcome code (`success/partial/fail/abstain/bypassed`)
- what degraded, why, and whether verification passed
- notable divergences (expected vs actual)

RS aggregates episodes into human-readable learning.

### DS (Drift Signal) — structured runtime failure modes
RAL emits drift types:
- `time` (deadline/P99 spikes)
- `freshness` (TTL/TOCTOU breaches)
- `fallback` / `bypass`
- `verify` (postcondition fail)
- `outcome` (unexpected effects)
- `fanout` / `contention`

Each drift has severity + fingerprint + recommended patch type.

### MG (Memory Graph) — instant “why retrieval” + recurrence intelligence
RAL contributes nodes/edges:
- DecisionEpisode nodes (sealed)
- Action nodes (by idempotencyKey and targetRefs)
- Drift fingerprint nodes (recurrence, severity)
- Patch nodes (what changed, when, why)
- Provenance edges (evidenceRefs → decision)

MG enables sub-60s “why did we do this?” retrieval.

---

## 4) LLM Data Model requirements (agent-safe data)

To support RAL, data records must carry **freshness + provenance + operability**.

### Minimum fields (per feature/tool output)
- `value`
- `capturedAt` (ISO timestamp)
- `sourceRef` (system/path/query id)
- `ttlMs` (or inherited DTE default)
- optional: `confidence`, `lineageRef`, `policyTag`

### Action record requirements
- `blastRadiusTier`
- `idempotencyKey`
- `rollbackPlan`
- `authorization.mode` (`auto/hitl/blocked`)
- execution budgets (`timeoutMs`, retries)

### Episode + drift as first-class entities
- `DecisionEpisode` (sealed)
- `DriftEvent` (typed, fingerprinted)
- patch objects that link drift → change → outcomes

---

## 5) Runtime sequence (tool → action → verify → seal → drift)

```text
1) submit_task(decisionType)  → loads DTE
2) tool_execute(...)          → returns {result, capturedAt, sourceRef}
3) TTL/TOCTOU gate            → stale? degrade/abstain
4) action_dispatch(contract)  → enforce idempotency/rollback/auth
5) verify_run(method)         → read-after-write / postcondition
6) episode_seal               → hash + seal DecisionEpisode
7) drift_emit (if needed)     → typed drift + fingerprint → patch workflow
```

---

## 6) What stays optional vs what becomes standard

**Optional (module):**
- RAL supervisor runtime
- MCP gateway/server
- verifiers library and action dispatchers

**Standardized (contracts + data):**
- DTE and Action Contract schemas
- capturedAt/TTL/provenance fields
- DecisionEpisode + DriftEvent records

---

## 7) One-line integration statement (canonical)
**Coherence Ops defines the governance loop. RAL/Σ OVERWATCH enforces it at runtime and emits sealed episodes + drift that automatically populate DLR / RS / DS / MG — powered by an LLM Data Model with timestamps, TTL, provenance, and action contracts.**
