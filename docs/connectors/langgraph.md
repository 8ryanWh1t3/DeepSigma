# LangGraph Connector

Ingests LangGraph execution traces as Coherence Ops evidence, enabling drift detection over AI decision pipelines.

## Overview

The LangGraph connector (`adapters/langgraph/connector.py`) maps LLM chain execution traces to canonical records with `RecordEnvelope` wrappers. It has **no runtime dependency** on langchain or langgraph — it only parses trace JSON.

This is complementary to the existing `LangGraphExhaustTracker` (`adapters/langgraph_exhaust.py`), which captures real-time execution events. The connector is designed for **post-hoc trace ingestion** from files, APIs, or LangSmith exports.

## Supported Formats

### 1. LangSmith Run (flat list)

A list of Run objects as exported from LangSmith or a custom `BaseTracer`:

```json
[
  {
    "id": "run-001",
    "name": "agent",
    "run_type": "chain",
    "start_time": "2026-02-18T10:00:00Z",
    "end_time": "2026-02-18T10:00:02Z",
    "status": "success",
    "inputs": { ... },
    "outputs": { ... },
    "trace_id": "trace-abc",
    "parent_run_id": null,
    "extra": {
      "metadata": {
        "langgraph_step": 1,
        "langgraph_node": "agent",
        "langgraph_triggers": ["start:agent"]
      }
    }
  }
]
```

### 2. LangSmith Run (nested tree)

A single root Run dict with `child_runs` arrays (automatically flattened):

```json
{
  "id": "root",
  "run_type": "chain",
  "child_runs": [
    { "id": "child-1", "run_type": "llm", "child_runs": [] }
  ]
}
```

### 3. astream_events v2

The streaming event format from `graph.astream_events(input, version="v2")`:

```json
[
  { "event": "on_chain_start", "name": "agent", "run_id": "r1", ... },
  { "event": "on_chain_end", "name": "agent", "run_id": "r1", ... },
  { "event": "on_tool_start", "name": "search", "run_id": "r2", ... },
  { "event": "on_tool_end", "name": "search", "run_id": "r2", ... }
]
```

Streaming chunk events (`*_stream`) are automatically skipped.

## Record Type Mapping

| `run_type` | `record_type` | Confidence | TTL |
|-----------|--------------|------------|-----|
| `llm` | `Claim` | 0.75 | 5 min |
| `tool` | `Event` | 0.90 | 10 min |
| `retriever` | `Document` | 0.80 | 10 min |
| `chain` | `Event` | 0.85 | 5 min |

## Provenance

Each record's provenance URI follows the pattern:

```
langgraph://{graph_id}/{node_name}?step={step}
```

## Chain-of-Thought Links

Edges between graph nodes are reconstructed from `langgraph_triggers` metadata. Each trigger produces a `derived_from` link connecting the current node to the triggering node.

## Usage

```python
from adapters.langgraph.connector import LangGraphConnector

# Initialize with a graph identifier
connector = LangGraphConnector(
    graph_id="revenue-agent",
    source_instance="production",
)

# Ingest trace data (auto-detects format)
trace_data = json.loads(Path("trace.json").read_text())
records = connector.to_canonical(trace_data)

# Wrap in standard envelopes
envelopes = connector.to_envelopes(records)

# Validate
from connectors.contract import validate_envelope
for env in envelopes:
    errors = validate_envelope(env.to_dict())
    assert not errors
```

## Testing

```bash
pytest tests/test_langgraph_connector.py -v
```

Fixtures are in `fixtures/connectors/langgraph_small/`:
- `baseline_raw.json` — 5-run LangSmith trace (agent, LLM, tool, retriever, final agent)
- `delta_raw.json` — 1-run error case (permission denied)
- `expected_envelopes.jsonl` — golden envelope output for deterministic comparison
