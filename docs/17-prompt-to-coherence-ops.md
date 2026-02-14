# Prompt Engineering → Coherence Ops Translator

> How we stop "prompt vibes" and ship institutional reliability.

## The Problem

Prompts are handwritten runtime code.
They drift, they break, and they can't be audited.

When a prompt says "always," "never," "must," or "if X then Y" — that's a policy.
When it's embedded in prose, it's invisible to tests, unreachable by tooling,
and impossible to version.

Prompt engineering optimizes **one call**.
Coherence Engineering operationalizes **every call**.

## The Translation Move

We don't "write better prompts."
We compile prompts into an operating system: types, policies, events, and renderers.

### 1) Types (Data Model)

Every claim an LLM touches must have structure:

| Type | Purpose | RAL / Coherence Ops Mapping |
|------|---------|----------------------------|
| **Claim** | An assertion the system makes or consumes | `DecisionEpisode.plan`, tool output `value` |
| **Evidence** | Data backing a claim | `evidenceRefs[]`, feature records with `capturedAt` |
| **Source** | Origin + freshness of evidence | `sourceRef`, `capturedAt`, `ttlMs` |
| **Assumption** | Unstated belief with an expiry | `ttlMs`, `maxFeatureAgeMs`, `assumption.halfLife` |
| **Drift** | Detected divergence from expected state | `DriftEvent` (typed, fingerprinted) |
| **Patch** | Corrective change triggered by drift | Patch node in Memory Graph |
| **Memory** | Sealed, immutable record of a decision | `DecisionEpisode` (sealed, hashed) |

See: [02-core-concepts.md](02-core-concepts.md), [10-coherence-ops-integration.md](10-coherence-ops-integration.md)

### 2) Policies (Invariants)

Anything a prompt expresses as a rule belongs in a **Policy Pack**, not prose.

| Prompt Pattern | Policy Translation | Enforcement |
|----------------|-------------------|-------------|
| "Always cite sources" | `Claim → Evidence → Source` chain required | Verifier rejects episodes missing `evidenceRefs` |
| "Never overwrite previous answers" | `Seal → Version → Patch` (append-only) | `sealHash` immutability; patches link to prior episode |
| "Information may be outdated" | Assumption TTL / half-life | `ttlMs` gate; stale → degrade ladder fires |
| "Do not execute, only recommend" | `authorization.mode = recommend_only` | Safe Action Contract blocks `auto` dispatch |

See: [11-policy-packs.md](11-policy-packs.md), [12-degrade-ladder.md](12-degrade-ladder.md)

### 3) Events (State Machine)

Prompts hide control flow in natural language.
Coherence Ops makes it explicit:

| Trigger Condition | Event | System Response |
|-------------------|-------|-----------------|
| Evidence missing for a claim | `drift.type = verify` | Ask clarifying questions; do not proceed |
| Contradiction between sources | `drift.type = freshness` or `contention` | Emit DriftSignal with fingerprint |
| Drift detected | `DriftEvent` | Trigger Patch workflow (see drift→patch cycle) |
| Patch applied | `PatchNode` created | Update Memory Graph; link to originating drift |
| Deadline exceeded | `drift.type = time` | Degrade ladder fires (cache → small_model → rules_only → hitl → abstain) |

See: [10-coherence-ops-integration.md § Drift Signal](10-coherence-ops-integration.md), [12-degrade-ladder.md](12-degrade-ladder.md)

### 4) Renderers (Prompt Compiler)

When a prompt *is* still needed (e.g., the final LLM call), it is **compiled**, not authored:

```
Lens + Objective + Allowed Context → JSON Schema output
```

- **Lens**: the role/perspective the model adopts (maps to `decisionType`)
- **Objective**: what the model must produce (maps to DTE `plan` stage)
- **Allowed Context**: evidence that passed TTL/TOCTOU gates (maps to `evidenceRefs`)
- **Output Schema**: a JSON Schema the response must conform to

No schema = no trust.
The renderer is deterministic given its inputs; the LLM fills in the reasoning.

## What You Get

| Capability | Prompt Engineering | Coherence Engineering |
|-----------|-------------------|----------------------|
| Repeatability | Hope + temperature=0 | Policy Pack + DTE + sealed episodes |
| Testability | Manual spot checks | Golden tests against `DecisionEpisode` schema |
| Auditability | Grep the prompt | DLR / RS / DS / MG with provenance chains |
| Portability | Rewrite per model | Model-agnostic; swap LLM, keep policies |
| Reliability | "It usually works" | Contractual: passes verification or degrades gracefully |

## Rule of Thumb

> If a prompt says **"always / never / must / if X then Y"**
> …it belongs in **policy + events + tests**, not prose.

Checklist for translating a prompt into Coherence Ops:

1. **Extract claims** — every assertion becomes a typed `Claim` with required `Evidence`.
2. **Identify sources** — every piece of evidence gets `sourceRef`, `capturedAt`, `ttlMs`.
3. **Surface assumptions** — anything unstated gets an explicit TTL / half-life.
4. **Encode rules as policies** — "always/never/must" → Policy Pack invariants.
5. **Map control flow to events** — "if X then Y" → DriftEvent triggers + degrade ladder.
6. **Define the output schema** — the renderer's JSON Schema replaces freeform output.
7. **Write golden tests** — expected `DecisionEpisode` shape for known inputs.

## Result

Prompt engineering becomes **Coherence Engineering**:

**Truth · Reasoning · Memory — operationalized.**

The prompt doesn't disappear — it becomes the last mile of a system
that has already enforced freshness, verified evidence, sealed decisions,
and prepared a degrade path before the LLM ever sees a token.

---

See also:
- [00-vision.md](00-vision.md) — project vision
- [02-core-concepts.md](02-core-concepts.md) — DTE, Safe Action Contract, DecisionEpisode, DriftEvent
- [10-coherence-ops-integration.md](10-coherence-ops-integration.md) — canonical artifact mapping (DLR/RS/DS/MG)
- [11-policy-packs.md](11-policy-packs.md) — portable, versioned policy bundles
- [13-verifiers.md](13-verifiers.md) — verification methods
