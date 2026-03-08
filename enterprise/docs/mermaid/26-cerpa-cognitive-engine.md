# 26 — CERPA Cognitive Engine & Context Envelope

Context Envelope wraps every CERPA cycle — carrying WHO, WHEN, WHERE, WHY, CONSTRAINTS, and SCOPE through the five-primitive adaptation loop. Context is NOT a primitive; it is ambient infrastructure.

```mermaid
graph TB
    subgraph "Context Sources"
        CS1[AuthorityOps<br/>actor, authority_id, delegation]
        CS2[DTE Spec<br/>deadline, budgets, freshness]
        CS3[Policy Pack<br/>policy_refs, pack_id, constraints]
        CS4[Episode State<br/>episode_id, cycle_id, domain]
    end

    subgraph "Context Envelope Builder"
        BLD[ContextEnvelopeBuilder]
        BLD --> |with_actor| WHO[WHO<br/>actor_id, actor_type<br/>authority_id, delegation_chain]
        BLD --> |with_dte| WHEN[WHEN<br/>deadline_ms, stage_budgets_ms<br/>started_at]
        BLD --> |with_domain| WHERE[WHERE<br/>domain, scope<br/>blast_radius_tier]
        BLD --> |with_goal| WHY[WHY<br/>goal, rationale<br/>policy_refs, policy_pack_id]
        BLD --> |with_dte| CONSTRAINTS[CONSTRAINTS<br/>dte_spec, freshness_ttl_ms<br/>max_hops, max_chain_depth]
        BLD --> |with_episode| SCOPE[SCOPE<br/>episode_id, cycle_id<br/>parent_context_id, tags]
        WHO --> ENV[ContextEnvelope]
        WHEN --> ENV
        WHERE --> ENV
        WHY --> ENV
        CONSTRAINTS --> ENV
        SCOPE --> ENV
    end

    subgraph "CERPA Cycle (5 Primitives)"
        P1[CLAIM<br/>asserted truth]
        P2[EVENT<br/>observable occurrence]
        P3[REVIEW<br/>evaluate claim vs event]
        P4[PATCH<br/>corrective action]
        P5[APPLY<br/>execute patch]
        P1 --> P2 --> P3 --> P4 --> P5
    end

    subgraph "Context Flow"
        CF1[CerpaCycle.context]
        CF2[Review.metadata.context_ref]
        CF3[Patch.metadata.context_ref]
        CF4[ApplyResult.metadata.context_ref]
        CF5[FunctionResult.context_snapshot]
    end

    subgraph "Context Propagation"
        CP1[inherit_context<br/>parent → child]
        CP2[fork_context<br/>1 → N branches]
        CP3[merge_context<br/>N → 1 converge]
        CP4[snapshot_context<br/>→ MG storage]
        CP5[compute_context_diff<br/>before vs after]
    end

    subgraph "Memory Graph"
        MG_SNAP[CONTEXT_SNAPSHOT<br/>NodeKind]
        MG_EDGE[CONTEXTUALIZED_BY<br/>EdgeKind]
        MG_SNAP --- MG_EDGE
    end

    CS1 --> BLD
    CS2 --> BLD
    CS3 --> BLD
    CS4 --> BLD

    ENV -.->|wraps| P1
    ENV -.->|wraps| P2
    ENV -.->|wraps| P3
    ENV -.->|wraps| P4
    ENV -.->|wraps| P5

    ENV --> CF1
    P3 -.-> CF2
    P4 -.-> CF3
    P5 -.-> CF4

    ENV --> CP1
    CP1 -->|cascade propagate| CF5
    CP4 --> MG_SNAP
    CF1 --> CP5
```

## Context Is NOT a Primitive

The ContextEnvelope is a transport type — it flows through the system but:
- Has no `primitive_type` field
- Is not in the `PrimitiveType` enum
- Never calls `wrap_primitive()`
- Is not counted by the Five-Primitive Guard

## Six Context Dimensions

| Dimension | Fields | Source |
|-----------|--------|--------|
| **WHO** | `actor_id`, `actor_type`, `authority_id`, `delegation_chain` | AuthorityOps |
| **WHEN** | `deadline_ms`, `stage_budgets_ms`, `started_at` | DTE Spec |
| **WHERE** | `domain`, `scope`, `blast_radius_tier` | Episode / Domain Mode |
| **WHY** | `goal`, `rationale`, `policy_refs`, `policy_pack_id` | Policy Pack |
| **CONSTRAINTS** | `dte_spec`, `freshness_ttl_ms`, `max_hops`, `max_chain_depth`, `action_constraints` | DTE + Policy |
| **SCOPE** | `episode_id`, `cycle_id`, `parent_context_id`, `related_entity_ids`, `tags` | Episode State |

## Propagation Semantics

| Operation | When | Behavior |
|-----------|------|----------|
| **inherit** | Cascade to child domain | New ID, `parent_context_id` → parent, domain override |
| **fork** | Multi-target cascade | N independent branches from one parent |
| **merge** | Converging branches | Primary wins scalars, collections union |
| **snapshot** | MG persistence | Immutable capture with trigger label |
| **diff** | Change tracking | Changed/added/removed field comparison |

## Support Modules

| Module | Purpose | File |
|--------|---------|------|
| ContextEnvelope | 6-dimension ambient context | `src/core/context/models.py` |
| ContextEnvelopeBuilder | Fluent builder from authority/DTE/policy/episode | `src/core/context/builder.py` |
| Context Propagation | inherit, fork, merge, snapshot, diff | `src/core/context/propagation.py` |
| Context Validators | Envelope validation rules | `src/core/context/validators.py` |
