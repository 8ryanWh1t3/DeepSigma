# Action Contract Schema

The **Safe Action Contract** is the governance contract that an agent must satisfy before any action is dispatched. It encodes blast radius, idempotency, rollback, and authorization so that every tool call can be audited and reversed.

**Schema file**: [`specs/action_contract.schema.json`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/schemas/core/action_contract.schema.json)

---

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `actionId` | string | Stable, unique action identifier. Never reused. |
| `actionType` | string | Logical name of the action (e.g., `quarantine_account`, `send_alert`). |
| `blastRadiusTier` | enum | Potential impact scope: `tiny` / `small` / `medium` / `large`. |
| `targetRefs` | array | One or more `{type, id}` objects identifying the affected resources. |
| `constraints` | object | Policy/budget/scope constraints: rate limits, change windows, scope bounds. |
| `authorization` | object | Auth mode + optional policy reference and approver. See below. |
| `idempotencyKey` | string | Stable key ensuring the action has the same effect if replayed. |
| `rollbackPlan` | object | How the action can be reversed. See below. |

---

## Authorization

| Field | Type | Values / Description |
|-------|------|---------------------|
| `mode` | enum | `auto` — dispatch without human approval |
|        |      | `hitl` — pause for human-in-the-loop approval |
|        |      | `blocked` — action not permitted under current policy |
| `policyRef` | string | Optional ID of the policy pack that determined the mode |
| `approver` | string | Role or identity required for `hitl` approval |

---

## Rollback Plan

| Field | Type | Values / Description |
|-------|------|---------------------|
| `type` | enum | `none` — no rollback possible (action is irreversible by design) |
|        |      | `compensate` — issue a compensating action |
|        |      | `restore` — restore from snapshot or backup |
|        |      | `revert` — undo the mutation (e.g., delete a created record) |
| `instructions` | object | Free-form instructions for the rollback procedure |
| `timeoutMs` | integer | Maximum time allowed for rollback execution |

---

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `preconditions` | array | Declarative checks that must pass before dispatch (e.g., TTL ok, resource state matches). |
| `execution.executionSloMs` | integer | Target execution time (informational SLO). |
| `execution.timeoutMs` | integer | Hard timeout — abort and rollback if exceeded. |
| `execution.retryPolicy.maxRetries` | integer | Number of retry attempts on transient failure. |
| `execution.retryPolicy.backoffMs` | integer | Delay between retries (ms). |

---

## Blast Radius Tiers

| Tier | Scope | Typical Actions |
|------|-------|----------------|
| `tiny` | Single record, read-only or append | Log entry, status read |
| `small` | Single record, mutating | Update flag, soft-delete record |
| `medium` | Multiple records or single high-value record | Account suspension, batch update |
| `large` | Cross-system or irreversible at scale | Mass notification, infrastructure change |

Blast radius determines whether verification is required (controlled by the DTE `verification.requiredAboveBlastRadius` field) and whether `hitl` authorization applies.

---

## Relationship to Other Schemas

- **[DTE Schema](DTE-Schema)** — sets `blastRadiusMax` and `requireRollbackAbove` constraints that the action contract must satisfy
- **[Episode Schema](Episode-Schema)** — the episode's `actions` array embeds the action contract ref
- **[Drift Schema](Drift-Schema)** — `bypass` drift type fires when an action is dispatched without a valid contract

---

## Related Pages

- [Contracts](Contracts) — overview of all four contract types
- [Sealing & Episodes](Sealing-and-Episodes) — how action contracts are stamped into sealed episodes
- [Degrade Ladder](Degrade-Ladder) — how blast radius tiers interact with degrade steps
- [Schemas](Schemas) — all JSON Schema specs
