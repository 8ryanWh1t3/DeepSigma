# Context Envelope

The **ContextEnvelope** is structured ambient context that wraps every CERPA cycle. It carries six dimensions — WHO, WHEN, WHERE, WHY, CONSTRAINTS, SCOPE — through the five-primitive adaptation loop.

> **Context is NOT a primitive.** It is a transport type with no `primitive_type` field. The Five-Primitive Guard passes unchanged.

---

## Why Context Matters

Without context, primitives are unanchored:

- A **Claim** without WHO has no authority source
- A **Review** without WHEN has no deadline awareness
- A **Patch** without WHERE has unknown blast radius
- An **Apply** without WHY has no rationale chain

Context makes every CERPA stage self-describing without inflating the primitive model.

---

## Six Dimensions

| Dimension | Fields | Description |
|-----------|--------|-------------|
| **WHO** | `actor_id`, `actor_type`, `authority_id`, `delegation_chain` | Identity and authority provenance |
| **WHEN** | `deadline_ms`, `stage_budgets_ms`, `started_at` | Timing constraints from DTE |
| **WHERE** | `domain`, `scope`, `blast_radius_tier` | Operational scope and impact |
| **WHY** | `goal`, `rationale`, `policy_refs`, `policy_pack_id` | Decision rationale and policy |
| **CONSTRAINTS** | `dte_spec`, `freshness_ttl_ms`, `max_hops`, `max_chain_depth`, `action_constraints` | Execution limits |
| **SCOPE** | `episode_id`, `cycle_id`, `parent_context_id`, `related_entity_ids`, `tags` | Episode and lineage |

Plus: `context_id` (CTX-{hex12}), `created_at`, `metadata`.

---

## Builder Usage

```python
from src.core.context import ContextEnvelopeBuilder

ctx = (ContextEnvelopeBuilder()
    .with_actor("agent-001", "agent")
    .with_domain("intelops")
    .with_dte(dte_spec)
    .with_episode("EP-abc123")
    .with_goal("resolve drift", "confidence dropped below threshold")
    .with_blast_radius("medium")
    .build())
```

Bootstrap from an existing handler ctx dict:

```python
ctx = ContextEnvelopeBuilder.from_ctx_dict(handler_ctx).build()
```

---

## Propagation

| Operation | When | Behavior |
|-----------|------|----------|
| `inherit_context(parent)` | Cascade to child domain | New ID, links via `parent_context_id`, optional domain override |
| `fork_context(parent, targets)` | Multi-target cascade | N independent branches |
| `merge_context(primary, *others)` | Converging branches | Primary wins scalars, collections union |
| `snapshot_context(env, trigger)` | MG persistence | Immutable capture with trigger label |
| `compute_context_diff(before, after)` | Change tracking | Changed/added/removed field comparison |

---

## CERPA Integration

The `CerpaCycle` dataclass carries an optional `context` field:

```python
cycle = run_cerpa_cycle(claim, event, context=ctx)
# cycle.context -> ContextEnvelope
# cycle.to_dict() includes "context": {...}
```

The engine stamps `context_ref` into Review, Patch, and ApplyResult metadata.

---

## Memory Graph Integration

Context snapshots persist to the Memory Graph:

- **NodeKind**: `CONTEXT_SNAPSHOT`
- **EdgeKind**: `CONTEXTUALIZED_BY` (links nodes to their context)

```python
from src.core.context import snapshot_context
snap = snapshot_context(ctx, trigger="cerpa_review")
mg.add_context_snapshot(snap, linked_node_ids=["EP-001"])
```

---

## Cascade Propagation

When the CascadeEngine propagates events cross-domain, it automatically inherits context for each child invocation:

```python
child_env = inherit_context(parent_env, new_domain=rule.target_domain)
```

This ensures every cascaded handler receives proper context lineage.

---

## Validation

```python
from src.core.context import validate_context_envelope

errors = validate_context_envelope(ctx)
# [] if valid
# ["context_id must start with 'CTX-'", ...] if invalid
```

Checks: context_id format, blast_radius_tier, actor_type, positive deadline/freshness/max_hops.

---

## Architecture Diagram

See [26 — CERPA Cognitive Engine](../mermaid/26-cerpa-cognitive-engine.md) for the full Mermaid diagram.
