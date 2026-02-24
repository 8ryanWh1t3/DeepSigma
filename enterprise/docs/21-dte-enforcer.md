# DTE Enforcer

Active constraint validation for Decision Timing Envelopes.

The `DTEEnforcer` validates runtime signals (elapsed time, stage budgets, feature freshness, operational limits) against a DTE spec and returns typed violations. It complements the degrade ladder -- the enforcer detects breaches, the caller decides whether to abort, degrade, or log.

**Source:** `engine/dte_enforcer.py`

---

## Setup

No extra dependencies. Part of the core `engine` package.

```python
from engine.dte_enforcer import DTEEnforcer, DTEViolation
```

---

## Usage

### Basic enforcement

```python
dte_spec = {
    "deadlineMs": 100,
    "stageBudgetsMs": {"context": 40, "plan": 30, "act": 20, "verify": 10},
    "freshness": {
        "defaultTtlMs": 500,
        "featureTtls": {"price_feed": 300},
        "allowStaleIfSafe": False,
    },
    "limits": {"maxHops": 5, "maxToolCalls": 15, "maxFanout": 3, "maxChainDepth": 4},
}

enforcer = DTEEnforcer(dte_spec)

violations = enforcer.enforce(
    elapsed_ms=95,
    stage_elapsed={"context": 40, "plan": 30, "act": 20, "verify": 5},
    feature_ages={"price_feed": 350, "user_profile": 100},
    counts={"hops": 3, "tool_calls": 12},
)

if violations:
    for v in violations:
        print(f"[{v.severity}] {v.gate}: {v.message}")
```

### Supervisor integration

```python
violations = enforcer.enforce(elapsed_ms=elapsed, counts=counts)
hard = [v for v in violations if v.severity == "hard"]
if hard:
    episode.outcome = "abstain"
    episode.degrade_rationale = hard[0].message
```

---

## API Reference

### `DTEEnforcer`

| Member | Description |
|---|---|
| `__init__(dte_spec: dict)` | Create an enforcer from a DTE spec dict. The spec follows the DTE JSON schema (`deadlineMs`, `stageBudgetsMs`, `freshness`, `limits`). |
| `enforce(elapsed_ms, stage_elapsed?, feature_ages?, counts?)` | Check all DTE constraints. Returns `list[DTEViolation]` (empty when within envelope). |

**Parameters for `enforce()`:**

| Parameter | Type | Description |
|---|---|---|
| `elapsed_ms` | `int` | Total elapsed time in milliseconds. |
| `stage_elapsed` | `dict[str, int]` | Per-stage elapsed time: `context`, `plan`, `act`, `verify`. |
| `feature_ages` | `dict[str, int]` | Feature name to age-in-ms mapping. |
| `counts` | `dict[str, int]` | Operational counters: `hops`, `fanout`, `tool_calls`, `chain_depth`. |

### `DTEViolation`

Dataclass representing a single constraint violation.

| Field | Type | Description |
|---|---|---|
| `gate` | `str` | Constraint category: `deadline`, `stage_budget`, `feature_ttl`, `limits` |
| `field` | `str` | Specific spec field, e.g. `stageBudgetsMs.plan` |
| `limit_value` | `Any` | The configured limit |
| `actual_value` | `Any` | The observed value |
| `severity` | `str` | `hard` (must abort/abstain) or `soft` (should degrade) |
| `message` | `str` | Human-readable description |

### Severity rules

| Gate | Severity |
|---|---|
| `deadline` | Always `hard` |
| `stage_budget` | Always `soft` |
| `feature_ttl` | `soft` if `allowStaleIfSafe` is true, else `hard` |
| `limits` | Always `hard` |

---

## CLI

```bash
coherence dte check --spec specs/dte_classify.json \
    --elapsed-ms 120 \
    --feature-ages price_feed=350,user_profile=100 \
    --counts hops=3,tool_calls=12
```

Exits `0` when no violations, `1` on soft violations, `2` on hard violations.

---

## Files

| File | Path |
|---|---|
| Source | `engine/dte_enforcer.py` |
| DTE Schema | `specs/dte.schema.json` |
| This doc | `docs/21-dte-enforcer.md` |
