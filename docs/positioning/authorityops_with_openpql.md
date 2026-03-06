# AuthorityOps with OpenPQL

## What Is OpenPQL?

OpenPQL (Open Policy Query Language) is the policy evaluation language used inside AuthorityOps. It is not a general-purpose query language. It is a deterministic compilation and evaluation pipeline that transforms decision reasoning into enforceable governance artifacts.

The core contract: a Decision Log Record (DLR) and a policy pack go in. A sealed governance artifact with constraints, reasoning requirements, and a hash comes out. The artifact is then evaluated step-by-step against the runtime context to produce a terminal verdict.

## How It Works: DLR to Governance Artifact

The OpenPQL compilation step is implemented in `src/core/authority/policy_compiler.py`.

```
DLR (from ReOps)  +  Policy Pack (from config)
        |                     |
        v                     v
  +---------------------------------+
  |    compile_policy()             |
  |    - Extract DLR ID, episode ID |
  |    - Compute seal hash (SHA-256)|
  |    - Bind DLR ref to artifact   |
  +---------------------------------+
               |
               v
    GovernanceArtifact
    {
      artifact_id:   "GOV-<hex>"
      artifact_type: "policy_evaluation"
      episode_id:    <from DLR>
      dlr_ref:       <DLR ID>
      seal_hash:     "sha256:<hex>"
      seal_version:  1
    }
```

The compilation is deterministic. Same DLR + same policy pack = same governance artifact (modulo timestamp). No side effects. Fully testable.

### Extracting Constraints

`extract_constraints()` pulls applicable constraints from the policy pack, filtered by action type:

- Constraints with an `appliesTo` list are scoped to specific action types.
- Constraints without `appliesTo` are universal.
- An implicit `requires_dlr` constraint is added when the policy requires DLR presence.
- An implicit `blast_radius_max` constraint is added when the policy specifies a maximum blast radius.

### Extracting Reasoning Requirements

`extract_reasoning_requirements()` compiles the reasoning threshold from the DLR and optional policy pack:

- `requires_dlr`: whether a DLR must exist (default: true)
- `minimum_claims`: minimum number of claims required
- `required_truth_types`: truth types that must be present (e.g., "observation", "assumption")
- `minimum_confidence`: minimum average confidence score (default: 0.7)
- `max_assumption_age`: maximum age for assumption-type claims (ISO 8601 duration)

## The Policy Evaluation Pipeline (11 Steps)

The compiled governance artifact feeds into the 11-step runtime evaluation pipeline in `src/core/authority/policy_runtime.py`. Each step is a pure function that receives the request and context, and returns a pass/fail result with an optional terminal verdict.

| Step | Name | Checks | Terminal Verdict on Failure |
|------|------|--------|-----------------------------|
| 1 | action_intake | Required fields: actionId, actionType, actorId, resourceRef | BLOCK |
| 2 | actor_resolve | Actor exists in registry | BLOCK |
| 3 | resource_resolve | Resource exists (non-blocking if unknown) | -- |
| 4 | policy_load | Policy pack found for action type (default allow if none) | -- |
| 5 | dlr_presence | DLR exists for this decision | MISSING_REASONING |
| 6 | assumption_validate | All assumption-type claims are fresh | EXPIRED |
| 7 | half_life_check | No claim half-lives have decayed past expiry | EXPIRED |
| 8 | blast_radius_threshold | Actual blast radius tier does not exceed policy maximum | ESCALATE |
| 9 | kill_switch_check | Kill switch is not active | KILL_SWITCH_ACTIVE |
| 10 | decision_gate | Aggregate all prior results (always passes if reached) | -- |
| 11 | audit_emit | Emit audit record (best-effort, always passes) | -- |

The pipeline short-circuits on critical failures: BLOCK, MISSING_REASONING, EXPIRED, KILL_SWITCH_ACTIVE. When a terminal verdict is reached, remaining steps are skipped and the audit record is emitted with the failing step recorded.

## Example Policy Evaluations

### Scenario 1: ALLOW

```
Request:
  actorId: "agent-trade-bot"
  actionType: "execute_trade"
  resourceRef: "portfolio-alpha"
  blastRadiusTier: "small"
  episodeId: "ep-2026-0042"

Context:
  actor_registry: { "agent-trade-bot": { actorType: "agent", roles: [...] } }
  policy_packs: { "execute_trade": { maxBlastRadius: "medium", requiresDlr: true } }
  dlr_store: { "ep-2026-0042": { ... } }
  claims: [ { truthType: "observation", halfLife: { expiresAt: "2026-03-06T..." } } ]
  kill_switch_active: false

Pipeline:
  action_intake       -> PASS  (all fields present)
  actor_resolve       -> PASS  (agent-trade-bot found)
  resource_resolve    -> PASS  (portfolio-alpha found)
  policy_load         -> PASS  (execute_trade policy loaded)
  dlr_presence        -> PASS  (ep-2026-0042 found in store)
  assumption_validate -> PASS  (no stale assumptions)
  half_life_check     -> PASS  (claims within half-life)
  blast_radius        -> PASS  (small <= medium)
  kill_switch_check   -> PASS  (not active)
  decision_gate       -> PASS
  audit_emit          -> PASS

Verdict: ALLOW
```

### Scenario 2: BLOCK (missing reasoning)

```
Request:
  actorId: "agent-deploy-bot"
  actionType: "deploy_service"
  resourceRef: "production-cluster"
  episodeId: "ep-2026-0099"

Context:
  dlr_store: {}       <-- no DLR exists
  policy_packs: { "deploy_service": { requiresDlr: true } }

Pipeline:
  action_intake       -> PASS
  actor_resolve       -> PASS
  resource_resolve    -> PASS
  policy_load         -> PASS
  dlr_presence        -> FAIL  (dlr_not_found:ep-2026-0099)
  [short-circuit]

Verdict: MISSING_REASONING
Audit: sealed with failed_checks: ["dlr_presence"]
```

### Scenario 3: ESCALATE (blast radius exceeded)

```
Request:
  actorId: "agent-migration-bot"
  actionType: "schema_migration"
  resourceRef: "core-database"
  blastRadiusTier: "large"

Context:
  policy_packs: { "schema_migration": { maxBlastRadius: "medium" } }
  dlr_store: { ... }  <-- DLR present
  claims: [...]        <-- all fresh

Pipeline:
  action_intake       -> PASS
  actor_resolve       -> PASS
  resource_resolve    -> PASS
  policy_load         -> PASS
  dlr_presence        -> PASS
  assumption_validate -> PASS
  half_life_check     -> PASS
  blast_radius        -> FAIL  (actual=large, max=medium)
  [short-circuit]

Verdict: ESCALATE
Audit: sealed with failed_checks: ["blast_radius_threshold"]
```

## Constraint Types

Seven constraint types are supported, defined in `ConstraintType` enum:

| Constraint | Expression Pattern | Purpose |
|------------|-------------------|---------|
| `time_window` | Temporal bounds for action execution | Restrict when actions can be performed |
| `blast_radius_max` | `blast_radius_tier <= {tier}` | Cap the damage scope of any single action |
| `requires_approval` | Approval path must be resolved | Gate on human approval before execution |
| `requires_dlr` | `dlr_ref IS NOT NULL` | Require a Decision Log Record with reasoning |
| `requires_reasoning` | Minimum claims and confidence threshold | Enforce reasoning quality, not just presence |
| `scope_limit` | Prefix-based scope overlap check | Restrict authority to specific resource domains |
| `rate_limit` | Action frequency cap | Prevent runaway autonomous execution |

Constraints are loaded from the policy pack, filtered by action type, and evaluated during the pipeline. Implicit constraints (DLR requirement, blast radius cap) are injected by the compiler when the policy specifies them.

## Policy Loading and Caching

Policies are loaded during step 4 (policy_load) of the evaluation pipeline:

1. **Lookup by action type.** The `policy_packs` dict in the evaluation context is keyed by action type (e.g., "execute_trade", "deploy_service").
2. **Fallback to default.** If no action-specific policy exists, the `default` policy pack is used.
3. **No policy = open policy.** If no policy pack is found at all, the pipeline continues with an empty policy (default allow). This is a deliberate design choice: policy absence is not a block condition. Missing policy is logged but not terminal.
4. **Context injection.** The loaded policy is stored in `context["_policy"]` for use by downstream steps (DLR requirement check, blast radius threshold, constraint evaluation).

Policy packs are passed into the evaluation context by the caller. The runtime does not manage a policy registry or cache layer -- that responsibility belongs to the domain mode or the orchestration layer above. This keeps the runtime pure: same inputs, same outputs, no hidden state.

## Seal and Hash Integrity

Every governance artifact produced by the compiler includes a SHA-256 seal hash computed from the canonical JSON of the DLR ID, policy pack ID, and compilation timestamp. This hash is deterministic and verifiable.

Audit records produced by the evaluation pipeline are hash-chained: each record's `chain_hash` is computed from its content, and `prev_chain_hash` links to the previous record. The chain is append-only and verifiable with `AuthorityAuditLog.verify_chain()`.

The chain answers two questions:
- Has any record been tampered with? (hash mismatch)
- Has any record been deleted or reordered? (chain break)

This is not signing. This is structural integrity. It ensures that the sequence of authority evaluations is reconstructable and tamper-evident.
