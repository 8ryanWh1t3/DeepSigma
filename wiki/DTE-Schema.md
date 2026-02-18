# DTE Schema — Decision Timing Envelope

The **Decision Timing Envelope (DTE)** is the per-`decisionType` contract that governs time budgets, freshness requirements, blast radius limits, degrade ladder ordering, and verification requirements. DTEs are loaded at runtime — typically from a Policy Pack — and stamped onto every sealed episode.

**Schema file**: [`specs/dte.schema.json`](../specs/dte.schema.json)

---

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `decisionType` | string | The decision class this DTE governs (e.g., `AccountQuarantine`). |
| `version` | string | Semantic version of this DTE definition. |
| `deadlineMs` | integer | Total wall-clock budget for the decision (milliseconds). |
| `stageBudgetsMs` | object | Per-stage time budgets. Must sum to ≤ `deadlineMs`. |
| `freshness` | object | TTL settings for context data. |
| `limits` | object | Structural limits on agent behaviour. |
| `degradeLadder` | array | Ordered steps the runtime uses when deadlines or freshness fail. |
| `verification` | object | When and how to verify action outcomes. |
| `safeAction` | object | Blast radius and rollback requirements for dispatched actions. |

---

## Stage Budgets

All four stages are required. Each value is a millisecond integer.

| Stage | Description |
|-------|-------------|
| `context` | Gather features, tool outputs, and evidence |
| `plan` | LLM or rule-based planning |
| `act` | Action dispatch and execution |
| `verify` | Postcondition verification |

---

## Freshness

| Field | Type | Description |
|-------|------|-------------|
| `defaultTtlMs` | integer | Maximum age of any context feature before TOCTOU breach fires |
| `featureTtls` | object | Per-feature overrides keyed by feature name (ms) |
| `allowStaleIfSafe` | boolean | If `true`, stale context is permitted when blast radius is below the configured threshold (default `false`) |

---

## Limits

Structural guardrails to prevent fanout and retry storms.

| Field | Description |
|-------|-------------|
| `maxHops` | Maximum number of agent hops in a chain |
| `maxFanout` | Maximum number of parallel sub-tasks |
| `maxToolCalls` | Maximum tool invocations per decision |
| `maxChainDepth` | Maximum chain depth before escalation |

---

## Degrade Ladder

An ordered array of degrade steps. The runtime walks this array when time, freshness, or verifier failures occur.

| Step | Behaviour |
|------|-----------|
| `cache_bundle` | Serve context from a pre-computed snapshot; skip live feature fetch |
| `small_model` | Swap to a smaller, lower-latency model for the plan stage |
| `rules_only` | Drop LLM entirely; use deterministic rule engine |
| `hitl` | Pause the decision and request human-in-the-loop approval |
| `abstain` | Refuse to act; emit a `DriftEvent` and return a safe no-op |
| `bypass` | Emergency override (logged at elevated severity; audit trail required) |

Each step may carry an optional `maxExtraMs` — additional time the runtime may spend on that step before advancing to the next rung.

---

## Verification

| Field | Type | Description |
|-------|------|-------------|
| `requiredAboveBlastRadius` | enum | Verification is mandatory for actions with blast radius strictly above this tier (`none` / `tiny` / `small` / `medium` / `large`) |
| `methods` | array | Allowed verifier identifiers (e.g., `read_after_write`, `invariant_check`) |
| `verifyTimeoutMs` | integer | Hard timeout for the verify stage |

---

## Safe Action Constraints

| Field | Type | Description |
|-------|------|-------------|
| `requireIdempotency` | boolean | All dispatched actions must carry an `idempotencyKey` |
| `requireRollbackAbove` | enum | Rollback plan required for blast radius strictly above this tier |
| `blastRadiusMax` | enum | Hard upper limit on blast radius — any action exceeding this is blocked |
| `allowedActionTypes` | array | Optional allowlist of `actionType` values |

---

## Policy Pack Binding

The optional `policyPack` block lets a DTE record the hash and version of the Policy Pack that produced it:

| Field | Description |
|-------|-------------|
| `policyPackHash` | SHA-256 of the originating Policy Pack |
| `policyPackVersion` | Version string of that Policy Pack |

---

## Relationship to Other Schemas

- **[Action Contract Schema](Action-Contract-Schema)** — each dispatched action is validated against the DTE's `safeAction` constraints
- **[Policy Pack Schema](Policy-Pack-Schema)** — Policy Packs embed DTE defaults per `decisionType`
- **[Episode Schema](Episode-Schema)** — sealed episodes record the `decisionType` and active degrade step
- **[Drift Schema](Drift-Schema)** — DTE violations (TTL breach, deadline overage) emit structured drift events

---

## Related Pages

- [Contracts](Contracts) — overview of all four contract types
- [Degrade Ladder](Degrade-Ladder) — how the runtime walks ladder steps at runtime
- [Policy Packs](Policy-Packs) — how DTEs are packaged and versioned
- [Schemas](Schemas) — all JSON Schema specs
