# LangGraph Exhaust Tracker

Async event tracker for LangGraph `astream_events()` output.

The `LangGraphExhaustTracker` captures graph node execution, edge traversal, and tool calls from LangGraph's streaming event API. Events are buffered and flushed to the DeepSigma Exhaust Inbox. Optionally enforces DTE constraints during graph execution, returning violations when limits are breached.

**Source:** `adapters/langgraph_exhaust.py`

---

## Setup

Requires LangGraph and a running Exhaust API endpoint:

```bash
pip install langgraph
```

No additional DeepSigma dependencies beyond the core engine.

---

## Usage

### Basic tracking

```python
from adapters.langgraph_exhaust import LangGraphExhaustTracker

tracker = LangGraphExhaustTracker(
    endpoint="http://localhost:8000/api/exhaust/events",
    project="my-project",
)

async for event in graph.astream_events(input, version="v2"):
    await tracker.handle_event(event)

await tracker.flush()
print(tracker.summary())
```

### With DTE enforcement

```python
from engine.dte_enforcer import DTEEnforcer
from adapters.langgraph_exhaust import LangGraphExhaustTracker

dte_spec = {
    "deadlineMs": 5000,
    "limits": {"maxHops": 10, "maxToolCalls": 20},
}
enforcer = DTEEnforcer(dte_spec)

tracker = LangGraphExhaustTracker(
    endpoint="http://localhost:8000/api/exhaust/events",
    project="my-project",
    dte_enforcer=enforcer,
    flush_interval=2.0,
)

async for event in graph.astream_events(input, version="v2"):
    violations = await tracker.handle_event(event)
    if violations:
        print(f"DTE violated: {violations}")
        break  # or degrade

await tracker.flush()
```

---

## API Reference

### `LangGraphExhaustTracker`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `str` | `http://localhost:8000/api/exhaust/events` | URL of the Exhaust events endpoint. |
| `project` | `str` | `"default"` | Project tag attached to every event. |
| `dte_enforcer` | `DTEEnforcer` | `None` | Optional DTE enforcer for constraint checking. |
| `flush_interval` | `float` | `1.0` | Seconds between automatic flushes. |

### Methods

| Method | Returns | Description |
|---|---|---|
| `handle_event(event)` | `list[dict] \| None` | Process one LangGraph event. Returns violation dicts on DTE breach, `None` otherwise. |
| `flush()` | `None` | Send buffered events to the exhaust endpoint. |
| `summary()` | `dict` | Return `{elapsed_ms, node_count, tool_call_count, violations}`. |

### Event mapping

LangGraph events are mapped to exhaust event types:

| LangGraph event | Exhaust event type | DTE check |
|---|---|---|
| `on_chain_start` (first) | `graph_start` | No |
| `on_chain_start` (subsequent) | `node_start` | No |
| `on_chain_end` | `node_end` | Yes |
| `on_tool_start` | `tool_start` | No |
| `on_tool_end` | `tool_end` | Yes |

DTE enforcement runs after `node_end` and `tool_end` events, checking elapsed time and counts (`hops`, `tool_calls`) against the DTE spec.

### Violation dict format

When DTE constraints are breached, `handle_event` returns a list of dicts:

```python
{
    "gate": "deadline",         # or "limits"
    "field": "deadlineMs",
    "limit": 5000,
    "actual": 5120,
    "severity": "hard",
    "message": "Deadline exceeded: 5120ms > 5000ms",
}
```

---

## Buffering and flush

Events are buffered in memory and flushed to the exhaust endpoint:
- Automatically when `flush_interval` seconds have elapsed since the last flush.
- Manually by calling `await tracker.flush()`.
- Always call `flush()` after the event loop completes to send remaining events.

The flush uses `urllib.request` and logs warnings on failure without raising.

---

## Files

| File | Path |
|---|---|
| Source | `adapters/langgraph_exhaust.py` |
| Helpers | `adapters/_exhaust_helpers.py` |
| This doc | `docs/23-langgraph-adapter.md` |
