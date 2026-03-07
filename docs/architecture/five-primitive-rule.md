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

### Coherence Loop (Canonical Write Path)

The coherence loop orchestrates the CERPA sequence:

```
CLAIM -> EVENT -> REVIEW -> PATCH -> APPLY
```

```python
from core import run_coherence_loop

result = run_coherence_loop(
    claim_payload={"id": "CLM-001", "text": "System is healthy", "domain": "ops"},
    event_payload={"id": "EVT-001", "text": "Latency spike", "domain": "ops"},
    source="my-module",
)
for step in result.steps:
    print(f"  {step.step.value}: {step.envelope.primitive_type}")
```

This is the canonical write path for producing envelopes. Direct
`wrap_primitive()` calls are valid but the coherence loop provides
sequencing, timing, and drift detection automatically.

Each step produces a `PrimitiveEnvelope`. The loop result contains
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
on every push and PR. It performs 7 check groups (18 total assertions):

1. `PrimitiveType` enum has exactly 5 members (3 assertions: count, values, frozenset)
2. `primitive_envelope.schema.json` enum values match (1 assertion)
3. No sixth primitive type defined in source (1 assertion)
4. Every `PrimitiveType` maps to a CERPA model class (5 assertions)
5. `wrap_primitive()` call-site scan — only 5 allowed types (1 assertion)
6. `NodeKind` alignment — `PRIMITIVE_TO_NODE_KIND` covers all 5 types (6 assertions)
7. No rogue primitive-type dataclasses in `core/*.py` (1 assertion)

### Authority Boundary

Envelopes are draft-grade until sealed via AuthorityOps.  No envelope
can approve itself, commit canon, or bypass the governance loop.

## Adding a Subtype

If you need a specialisation (e.g., `FactClaim`, `PolicyEvent`), use
the envelope `metadata` field or create a domain-specific wrapper.
Do not add a sixth `PrimitiveType` member.

## See Also

- [core_primitives.md](core_primitives.md) — archival-layer domain dataclasses,
  coexistence table, and file layout
