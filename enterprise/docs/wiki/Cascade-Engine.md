# Cascade Engine — Cross-Domain Event Propagation

> Events in one domain deterministically propagate to others.

## Overview

The Cascade Engine subscribes to all domain event streams, matches declarative rules, and invokes target handlers in the appropriate domain mode. Propagation is depth-limited to prevent infinite loops.

**Modules**:
- `src/core/modes/cascade.py` — engine
- `src/core/modes/cascade_rules.py` — rule definitions

## Rules

| Rule ID | Name | Source | Trigger | Target | Handler | Effect |
|---------|------|--------|---------|--------|---------|--------|
| CASCADE-R01 | `contradiction_triggers_review` | IntelOps | `claim_contradiction` | FranOps | FRAN-F03 | Canon enforcement check |
| CASCADE-R02 | `supersede_triggers_canon_update` | IntelOps | `claim_superseded` | FranOps | FRAN-F09 | Canon supersede workflow |
| CASCADE-R03 | `retcon_flags_episodes` | FranOps | `retcon_executed` | ReflectionOps | RE-F01 | Affected episodes flagged |
| CASCADE-R04 | `retcon_invalidates_claims` | FranOps | `retcon_cascade` | IntelOps | INTEL-F12 | Confidence recalc on dependents |
| CASCADE-R05 | `freeze_stales_claims` | ReflectionOps | `episodes_frozen` | IntelOps | INTEL-F11 | Half-life check on related claims |
| CASCADE-R06 | `killswitch_freezes_all` | ReflectionOps | `killswitch_activated` (red) | ReflectionOps | RE-F06 | All domains freeze |
| CASCADE-R07 | `red_drift_triggers_severity` | Any (`*`) | Any (`*`) with red severity | ReflectionOps | RE-F08 | Centralized severity scoring |

## How It Works

```python
engine = CascadeEngine()
engine.register_domain(intel)
engine.register_domain(fran)
engine.register_domain(reops)

result = engine.propagate(
    source_domain="franops",
    event={"subtype": "retcon_executed", ...},
    context=ctx,
    max_depth=3,
)
```

1. Engine receives an event with `source_domain` and `subtype`
2. `get_rules_for_event()` matches rules by domain, subtype, and severity filter
3. For each matching rule, the target handler is invoked
4. Handler output events are recursively cascaded (depth decremented)
5. `max_depth=0` halts propagation

## Rule Matching

A rule matches when ALL conditions are true:
- `source_domain` matches (or rule uses `*` wildcard)
- `source_subtype` matches (or rule uses `*` wildcard)
- `severity_filter` matches (or rule has no filter)

## CascadeResult

```python
@dataclass
class CascadeResult:
    triggered_rules: List[str]   # Rule IDs that fired
    results: List[FunctionResult] # Handler outputs
    errors: List[str]            # Any failures
```

## Depth Limiting

Default `max_depth=3`. Each recursive call decrements by 1. At depth 0, no further propagation occurs. This prevents circular cascades (e.g., R06 killswitch -> RE-F06 -> killswitch event -> R06 again).

## Cross-Domain Flow Diagram

See [Diagram 24 — Domain Modes & Cascade](../mermaid/24-domain-modes-cascade.md) for the full visual.

```
IntelOps ──[contradiction]──> FranOps (R01)
IntelOps ──[supersede]─────> FranOps (R02)
FranOps  ──[retcon]────────> ReflectionOps (R03)
FranOps  ──[retcon cascade]─> IntelOps (R04)
ReOps    ──[freeze]────────> IntelOps (R05)
ReOps    ──[killswitch]────> ReOps (R06)
Any      ──[red drift]────> ReOps (R07)
```

## Related Pages

- [IntelOps](IntelOps) — claim lifecycle domain
- [FranOps](FranOps) — canon enforcement domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [Event Contracts](Event-Contracts) — routing table
- [Drift to Patch](Drift-to-Patch) — drift lifecycle
