# Five-Primitive Rule

> Every object in the system is one of five types, a subtype, metadata,
> a derived view, or orchestration.  No sixth primitive may be introduced.

## The Five Primitives

| Type | Description | CERPA Model |
|------|-------------|-------------|
| CLAIM | An asserted truth or commitment to be monitored | `cerpa.models.Claim` |
| EVENT | An observable occurrence that may affect a Claim | `cerpa.models.Event` |
| REVIEW | Evaluation of a Claim against an Event | `cerpa.models.Review` |
| PATCH | Corrective action generated from a Review | `cerpa.models.Patch` |
| APPLY | Outcome of applying a Patch | `cerpa.models.ApplyResult` |

## Enforcement Surface

### PrimitiveType Enum

```python
from core.primitives import PrimitiveType, ALLOWED_PRIMITIVE_TYPES
```

`PrimitiveType` is a `str, Enum` with exactly five members.
`ALLOWED_PRIMITIVE_TYPES` is a `frozenset` of their string values.

### PrimitiveEnvelope

Every primitive flowing through the coherence loop, Memory Graph, or
FEEDS bus is wrapped in a `PrimitiveEnvelope`:

```python
from core.primitive_envelope import wrap_primitive, validate_envelope

env = wrap_primitive("claim", payload, source="my-module")
validate_envelope(env)  # raises ValueError for unknown types
```

Envelopes are append-only and versioned.  Superseding creates a new
envelope linked to its parent via `parent_envelope_id`.

### Coherence Loop

The coherence loop orchestrates the CERPA sequence:

```
CLAIM -> EVENT -> REVIEW -> PATCH -> APPLY
```

Each step produces a `PrimitiveEnvelope`.  The loop result contains
all step records with timing and notes.

### Memory Graph Mapping

Each `PrimitiveType` maps to a `NodeKind` in the Memory Graph:

| PrimitiveType | NodeKind |
|---------------|----------|
| CLAIM | CLAIM |
| EVENT | EPISODE |
| REVIEW | REVIEW |
| PATCH | PATCH |
| APPLY | APPLY |

Supersede chains produce `DERIVED_FROM` edges.  Coherence loop steps
produce `PRECEDED_BY` edges.

### CI Guard

The Five-Primitive Guard (`scripts/validate_five_primitives.py`) runs
on every push and PR.  It checks:

1. `PrimitiveType` enum has exactly 5 members
2. `primitive_envelope.schema.json` enum values match
3. No sixth primitive type defined in source
4. Every `PrimitiveType` maps to a CERPA model class

### Authority Boundary

Envelopes are draft-grade until sealed via AuthorityOps.  No envelope
can approve itself, commit canon, or bypass the governance loop.

## Adding a Subtype

If you need a specialisation (e.g., `FactClaim`, `PolicyEvent`), use
the envelope `metadata` field or create a domain-specific wrapper.
Do not add a sixth `PrimitiveType` member.
