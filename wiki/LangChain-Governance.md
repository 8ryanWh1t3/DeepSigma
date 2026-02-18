# LangChain Governance Adapter

DTE enforcement mid-chain via `GovernanceCallbackHandler`.

## Overview

The governance adapter intercepts every LLM and tool call inside a LangChain chain or agent, checks the active DTE constraints, and applies a configurable violation response: **raise**, **log**, or **degrade**.

This runs alongside (and composes with) the existing `ExhaustCallbackHandler` that captures telemetry.

## GovernanceCallbackHandler

```python
from deepsigma.adapters.langchain import GovernanceCallbackHandler

handler = GovernanceCallbackHandler(
    dte_id="dte-abc-123",
    violation_mode="raise",  # "raise" | "log" | "degrade"
)

chain = prompt | llm | parser
chain.invoke({"input": "..."}, config={"callbacks": [handler]})
```

### Hooks

| Callback | DTE Check |
|----------|-----------|
| `on_llm_start` | Token budget, TTL, model allowlist |
| `on_llm_end` | Actual token spend vs. remaining budget |
| `on_tool_start` | Tool in DTE scope, cost gate |
| `on_tool_end` | Verify output schema, latency cap |
| `on_chain_error` | Log violation context to exhaust |

## Violation Modes

| Mode | Behavior |
|------|----------|
| `raise` | Throw `DTEViolationError` immediately; chain aborts |
| `log` | Emit a warning-level exhaust event; chain continues |
| `degrade` | Trigger the [Degrade Ladder](Degrade-Ladder.md); substitute a safer fallback |

```python
from deepsigma.adapters.langchain import DTEViolationError

try:
    chain.invoke({"input": "..."}, config={"callbacks": [handler]})
except DTEViolationError as e:
    print(e.dte_id, e.field, e.actual, e.limit)
```

### DTEViolationError

| Attribute | Type | Description |
|-----------|------|-------------|
| `dte_id` | `str` | DTE that was violated |
| `field` | `str` | Constraint field (e.g. `token_budget`) |
| `actual` | `Any` | Observed value |
| `limit` | `Any` | DTE-defined limit |
| `mode` | `str` | Violation mode at time of error |

## Composability with ExhaustCallbackHandler

Both handlers can be passed together. Order does not matter -- they operate on independent callback hooks.

```python
from deepsigma.adapters.langchain import (
    GovernanceCallbackHandler,
    ExhaustCallbackHandler,
)

callbacks = [
    GovernanceCallbackHandler(dte_id="dte-abc-123", violation_mode="degrade"),
    ExhaustCallbackHandler(episode_id="ep-001"),
]

chain.invoke({"input": "..."}, config={"callbacks": callbacks})
```

The `ExhaustCallbackHandler` emits telemetry regardless of whether the governance handler raises, logs, or degrades.

## Comparison with LangGraph Tracker

| Feature | GovernanceCallbackHandler | LangGraph DTETracker |
|---------|--------------------------|----------------------|
| Runtime | LangChain LCEL chains | LangGraph state graphs |
| Enforcement point | Callback hooks | State node pre/post |
| Violation modes | raise / log / degrade | raise / log / degrade |
| Composability | Via callback list | Via graph middleware |
| Exhaust capture | Pair with ExhaustCallbackHandler | Built-in |

Choose **GovernanceCallbackHandler** for LCEL chains and **DTETracker** for LangGraph graphs. Both enforce the same DTE schema.

## Configuration

```yaml
# config/langchain.yaml
langchain:
  governance:
    default_violation_mode: raise
    dte_refresh_interval_s: 30
    degrade_ladder: default    # policy pack name
  exhaust:
    adapter: langchain
```

## Related

- [LangChain](LangChain.md)
- [DTE Schema](DTE-Schema.md)
- [Degrade Ladder](Degrade-Ladder.md)
- [Exhaust Inbox](Exhaust-Inbox.md)
