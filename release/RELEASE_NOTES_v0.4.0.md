---
title: "Release Notes — v0.4.0 Control Surface"
version: "0.4.0"
codename: "Control Surface"
date: "2026-02-18"
---

# v0.4.0 — Control Surface

**Release date:** 2026-02-18

> From passive audit to active enforcement — every decision constrained, every drift visible in real-time.

## What "Control Surface" Means

Before v0.4, Σ OVERWATCH could seal decisions, detect drift, score coherence, and close the Drift → Patch loop — but operators had no live view into the system, no active constraint enforcement during execution, and no way to plug into modern graph-execution frameworks. v0.4.0 adds the **control surfaces** that turn a governance framework into an operational control plane: a real-time SSE dashboard with Memory Graph visualization, a DTE Enforcer that validates timing constraints as decisions execute, runtime JSON Schema validation at ingest boundaries, and adapters for both LangChain and LangGraph.

## What's New

### Tier 1 — Persistence & Wiring

- **Memory Graph SQLite backend** — Optional persistent storage for the Memory Graph across sessions. Nodes and edges survive restarts without re-ingesting episodes.
- **Automated drift detector** — `detect_signals()` generates drift events from sealed episodes by comparing telemetry against DTE thresholds (time, freshness, fallback, bypass, verify, outcome).
- **IRIS MCP tools** — `iris.query` and `iris.reload` tools in the MCP server, with lazy pipeline loading from `DATA_DIR`. Any MCP client can now query IRIS directly.
- **Dashboard API server** — FastAPI backend serving real episode data through `/api/episodes`, `/api/drifts`, `/api/agents`, `/api/coherence`, and `POST /api/iris`.

### Tier 2 — Enforcement & Observability

- **OpenTelemetry instrumentation** — Spans for IRIS queries, coherence scoring, and MG operations. Counters and histograms for query timing, episode throughput, and drift severity. Drop-in integration with any OTel-compatible backend.
- **DTE Enforcer** — Active constraint validation for Decision Timing Envelopes. Checks deadline, per-stage budgets, feature TTL freshness, and operational limits (hops, fanout, tool calls, chain depth). Returns structured violation objects with gate, severity, and limit/actual values.
- **MCP resources & prompts** — `resources/list` and `resources/read` expose episodes, drift events, schemas, and coherence stats via URI-based access. Three operator prompt templates: `assemble_context`, `trace_decision`, `check_contradictions`.
- **Exhaust refiner hardening** — Entity typing for truth claims (person, org, system, concept, metric, event). Confidence calibration with source-type weighting for more accurate drift detection.

### Tier 3 — Ecosystem & Dashboard

- **Real-time SSE dashboard** — `GET /api/sse` streams episodes, drifts, agents, and Memory Graph data with 2-second change detection. Auto-reconnects on disconnect.
- **Zustand centralized store** — Replaces scattered `useState` with a typed store: episodes, drifts, agents, coherence, MG nodes/edges, connection state. Single source of truth for all dashboard components.
- **Memory Graph visualization** — SVG-based force-layout graph view with nodes colored by kind (Episode=blue, Action=green, Drift=yellow, Patch=purple, Evidence=gray, Claim=cyan). Click any node to inspect its properties.
- **LangGraph adapter** — Async `LangGraphExhaustTracker` for `astream_events()`. Tracks graph node execution and tool calls. Optional DTE enforcement during graph execution with violation reporting.
- **Runtime schema validation** — Lazy-compiled Draft 2020-12 validators with cross-schema `$ref` resolution. Validates episodes, policy packs, and drift signals against `specs/*.schema.json` at ingest boundaries.
- **Test infrastructure** — Shared `conftest.py` with factory fixtures, `pytest-benchmark` performance suite, and a 100-episode load test. CI now runs coverage gating and load tests.

## By the Numbers

| Metric | Value |
|--------|-------|
| Tests passing | 424 (up from 389) |
| New files | 17 |
| Modified files | 9 |
| New adapters | 3 (LangGraph, shared helpers, schema validator) |
| Dashboard views | 6 (Overview, Episodes, Drift, IRIS, MG Graph, Export) |
| MCP capabilities | Tools + Resources + Prompts |
| SSE event types | 4 (episodes, drifts, agents, mg) |

## Quick Start

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -e ".[dev]"

# Run the test suite
pytest tests/ -q
# Expected: 424 passed, 2 skipped

# Start the dashboard API
python dashboard/api_server.py
# Then open http://localhost:5173 (or run `cd dashboard && npm run dev`)

# Run the Money Demo
python -m coherence_ops.examples.drift_patch_cycle
```

## Verify

```bash
python -c "import coherence_ops; print(coherence_ops.__version__)"
# Expected: 0.4.0

pytest tests/ -q
# Expected: 424 passed, 2 skipped

cd dashboard && npm run build
# Expected: TypeScript compiles clean
```

## Key Links

| Resource | Path |
|----------|------|
| Changelog | [CHANGELOG.md](../CHANGELOG.md) |
| Dashboard store | [dashboard/src/store.ts](../dashboard/src/store.ts) |
| SSE hook | [dashboard/src/hooks/useSSE.ts](../dashboard/src/hooks/useSSE.ts) |
| MG Graph view | [dashboard/src/components/MGGraphView.tsx](../dashboard/src/components/MGGraphView.tsx) |
| DTE Enforcer | [engine/dte_enforcer.py](../engine/dte_enforcer.py) |
| Schema validator | [engine/schema_validator.py](../engine/schema_validator.py) |
| LangGraph adapter | [adapters/langgraph_exhaust.py](../adapters/langgraph_exhaust.py) |
| MCP server | [adapters/mcp/mcp_server_scaffold.py](../adapters/mcp/mcp_server_scaffold.py) |
| OTel instrumentation | [coherence_ops/otel.py](../coherence_ops/otel.py) |

---

**Σ OVERWATCH** — *Every decision constrained. Every drift visible. Every correction sealed.*
