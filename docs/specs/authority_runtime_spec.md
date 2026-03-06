# Runtime Gate Spec (Primitive 4)

## Purpose

Artifact-aware facade over the 11-step `policy_runtime.evaluate()` pipeline. Adds artifact reference tracking and structured `GateDecision` return type.

## Module

`src/core/authority/runtime_gate.py`

## GateDecision Model

```python
@dataclass
class GateDecision:
    gate_id: str                    # "RGATE-{12hex}"
    verdict: str                    # AuthorityVerdict value
    evaluated_at: str               # ISO 8601
    artifact_id: str                # from CompiledPolicy (empty if raw)
    policy_hash: str                # from CompiledPolicy (empty if raw)
    passed_checks: List[str]        # pipeline steps that passed
    failed_checks: List[str]        # pipeline steps that failed
    failed_reason: str              # "no_artifact" when compiled is None
    escalation_target: Optional[str]
```

## Evaluation Methods

### `evaluate(compiled, request, context) -> GateDecision`

1. If `compiled is None` → immediate `BLOCK` with `failed_reason="no_artifact"`
2. Otherwise delegates to `policy_runtime.evaluate(request, context)`
3. Wraps result with artifact metadata (`artifact_id`, `policy_hash`)

### `evaluate_raw(request, context) -> GateDecision`

Backward-compatible path with no artifact. Delegates directly to `policy_runtime.evaluate()`. `artifact_id` and `policy_hash` are empty.

## 8-Check Order (maps to 11-step pipeline)

| # | Check | Pipeline Step | Terminal Verdict |
|---|-------|---------------|-----------------|
| 1 | Action fields valid | `action_intake` | BLOCK |
| 2 | Kill switch clear | `kill_switch_check` | KILL_SWITCH_ACTIVE |
| 3 | Actor exists | `actor_resolve` | BLOCK |
| 4 | Resource exists | `resource_resolve` | -- |
| 5 | Policy loaded | `policy_load` | -- |
| 6 | DLR present | `dlr_presence` | MISSING_REASONING |
| 7 | Assumptions fresh | `assumption_validate` + `half_life_check` | EXPIRED |
| 8 | Blast radius within bounds | `blast_radius_threshold` | ESCALATE |

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `ALLOW` | All checks passed |
| `BLOCK` | Missing fields or unknown actor |
| `ESCALATE` | Blast radius exceeds policy maximum |
| `EXPIRED` | Stale assumptions or expired claim half-lives |
| `MISSING_REASONING` | No DLR exists for this decision |
| `KILL_SWITCH_ACTIVE` | Emergency kill switch is active |
