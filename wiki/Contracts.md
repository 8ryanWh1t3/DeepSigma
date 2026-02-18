# Contracts

RAL governance is expressed through four contract types. Each contract is a structured, versioned artifact that travels with the decision from planning through sealing.

---

## DTE — Decision Timing Envelope

**Schema:** [`specs/dte.schema.json`](../specs/dte.schema.json) · [Full reference →](DTE-Schema)

The DTE is the master budget and constraint contract for a `decisionType`. It defines:

- **`deadlineMs`** — total wall-clock budget for the entire decision
- **`stageBudgetsMs`** — per-stage budgets: `context`, `plan`, `act`, `verify`
- **`freshness`** — TTL settings for context features (defaultTtlMs + per-feature overrides)
- **`limits`** — structural guardrails: maxHops, maxFanout, maxToolCalls, maxChainDepth
- **`degradeLadder`** — ordered fallback steps when budgets or freshness fail
- **`verification`** — when verification is required and which methods are allowed
- **`safeAction`** — blast radius ceiling and rollback requirements

DTEs are loaded from a Policy Pack at decision start and stamped onto the sealed episode.

---

## Safe Action Contract

**Schema:** [`specs/action_contract.schema.json`](../specs/action_contract.schema.json) · [Full reference →](Action-Contract-Schema)

The Safe Action Contract is the per-dispatch governance contract that must be satisfied before any tool action is executed. It encodes:

- **`blastRadiusTier`** — potential impact scope: `tiny` / `small` / `medium` / `large`
- **`idempotencyKey`** — ensures the action is safe to replay without side effects
- **`rollbackPlan`** — how the action can be reversed: `none` / `compensate` / `restore` / `revert`
- **`authorization.mode`** — `auto` (dispatch immediately), `hitl` (pause for human approval), or `blocked`
- **`preconditions`** — declarative checks that must pass before dispatch
- **`targetRefs`** — the specific resources this action will affect

The supervisor validates the contract against the DTE's `safeAction` constraints before allowing dispatch. If the action's blast radius exceeds `blastRadiusMax` or authorization is blocked, the degrade ladder is consulted.

---

## Verification Contract

Verification is configured within the DTE (`verification` block) rather than as a separate JSON object. It specifies:

- **`requiredAboveBlastRadius`** — blast radius tier above which verification becomes mandatory
- **`methods`** — list of allowed verifier identifiers (e.g., `read_after_write`, `invariant_check`)
- **`verifyTimeoutMs`** — hard timeout for the verify stage

Verifiers run after action dispatch and return `pass`, `fail`, or `inconclusive`. Any non-pass outcome emits a `verify` DriftEvent.

See: [Verifiers](Verifiers) — implementation details and scaffold reference.

---

## DecisionEpisode

**Schema:** [`specs/episode.schema.json`](../specs/episode.schema.json) · [Full reference →](Episode-Schema)

The DecisionEpisode is not a pre-decision contract but the **sealed record** produced at the end of a decision cycle. It contains:

- **`episodeId`** — stable unique identifier
- **`decisionType`** — the type that governed this decision
- **Context** — the feature snapshot used (with `capturedAt` and TTL metadata)
- **Policy stamp** — `policyPackId`, `policyPackVersion`, `policyPackHash`
- **Degrade step** — which rung (if any) was activated, and the rationale
- **Verification** — method used, outcome, and details
- **`sealHash` + `sealedAt`** — SHA-256 of the episode (excluding the seal field itself)

Once sealed, an episode is immutable. All downstream analysis (DLR, Coherence Ops, IRIS) derives from sealed episodes.

---

## How the Contracts Interact

```
Policy Pack
    └─ DTE (one per decisionType)
            │
            ├─ stageBudgetsMs → governs each runtime stage
            ├─ freshness → gates context validity
            ├─ degradeLadder → fallback when budgets or freshness fail
            ├─ safeAction → constrains what the Action Contract may request
            └─ verification → governs when/how Verifiers run
                     │
                     └─ Safe Action Contract (one per dispatched action)
                              │
                              └─ Verified → DecisionEpisode (sealed)
```

---

## Related Pages

- [DTE Schema](DTE-Schema) — full DTE field reference
- [Action Contract Schema](Action-Contract-Schema) — full action contract field reference
- [Verifiers](Verifiers) — verifier scaffolds and custom implementation guide
- [Episode Schema](Episode-Schema) — sealed episode field reference
- [Policy Packs](Policy-Packs) — how DTEs are packaged and versioned
- [Schemas](Schemas) — all JSON Schema specs
