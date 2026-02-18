# Degrade Ladder

A **degrade ladder** is an ordered sequence of fallback steps the runtime walks when it cannot complete a decision within the nominal path. Each rung trades capability for safety: earlier rungs are gentler, later rungs are more conservative. The ladder is defined per `decisionType` in the DTE and stamped onto the sealed episode when a rung is activated.

The supervisor walks the ladder top-to-bottom, activating the lowest rung that brings the decision back within budget. If no rung resolves the issue, the decision emits a drift event and aborts.

---

## Rungs

| Rung | Behaviour | When to Use |
|------|-----------|-------------|
| `cache_bundle` | Serve context from a pre-computed snapshot; skip live feature fetch entirely | Context fetch is slow or stale; cached bundle is fresh enough for this decision type |
| `small_model` | Swap the plan stage to a smaller, lower-latency model | LLM response time is eating into the deadline; smaller model fits within remaining budget |
| `rules_only` | Drop the LLM entirely; use a deterministic rule engine for the plan stage | Model unavailable, too slow, or decision type has a deterministic rule path |
| `hitl` | Pause the decision and emit a human-in-the-loop approval request | Action blast radius is too high to proceed automatically; human sign-off required before continuing |
| `abstain` | Refuse to act; return a safe no-op result and emit a `DriftEvent` | No safe path exists within constraints; better to do nothing than to act unsafely |
| `bypass` | Emergency override — dispatch the action without completing the full governance chain | Production incident only; logged at elevated severity; full audit trail required |

> **Note:** `bypass` should be treated as a last resort. Every bypass emits a `bypass` DriftEvent with severity `red`. Policies should be reviewed after any bypass usage.

---

## Triggers

The supervisor evaluates ladder activation after each stage:

| Trigger | Stage | Typical Rung Activated |
|---------|-------|----------------------|
| Remaining budget < next-stage budget | Context / Plan | `cache_bundle` or `small_model` |
| P99 latency or jitter exceeds DTE threshold | Plan / Act | `small_model` or `rules_only` |
| TTL / TOCTOU breach (context stale) | Context | `cache_bundle` or `abstain` |
| Verifier returns `fail` or `inconclusive` | Verify | `hitl` or `abstain` |
| Blast radius exceeds `blastRadiusMax` without approval | Act | `hitl` or `abstain` |
| All rungs exhausted without resolution | Any | `abstain` (terminal) |

---

## Configuration

The ladder is defined as an ordered array in the DTE under `degradeLadder`. Each step may carry an optional `maxExtraMs` — additional time that step may consume before the runtime advances to the next rung:

```json
"degradeLadder": [
  { "step": "cache_bundle", "maxExtraMs": 200 },
  { "step": "small_model",  "maxExtraMs": 800 },
  { "step": "rules_only" },
  { "step": "hitl" },
  { "step": "abstain" }
]
```

---

## Episode Stamping

When a degrade step is activated, the supervisor stamps the sealed episode with:
- The activated `degrade_step` name
- A `degrade_rationale` string explaining which trigger fired

This makes every degrade visible in the DLR and queryable via IRIS `WHAT_CHANGED`.

---

## Related Pages

- [DTE Schema](DTE-Schema) — where the ladder is configured per decision type
- [Contracts](Contracts) — overview of all four contract types
- [Drift Schema](Drift-Schema) — drift types emitted during degrade (`fallback`, `bypass`, `verify`)
- [Verifiers](Verifiers) — verifier failure is a primary degrade trigger
- [Operations](Operations) — tuning ladders for production SLOs
