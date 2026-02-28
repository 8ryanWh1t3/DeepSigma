# OpenTelemetry

DeepSigma exports decision infrastructure telemetry via OpenTelemetry spans and metrics.

## Exporter

`OtelExporter` (`src/adapters/otel/exporter.py`) converts sealed episodes, drift events, coherence reports, tool calls, and LLM completions into OTel span trees and metrics.

**Exporter selection** (environment-based):
1. OTLP gRPC — `OTEL_EXPORTER_OTLP_ENDPOINT` set (port 4317)
2. OTLP HTTP — endpoint ends with `:4318` or `/v1/traces`
3. Console — fallback when no endpoint is configured

## Span Registry

All span names, attribute keys, and metric names are registered in `src/adapters/otel/spans.py`. The CI test `test_otel_span_registry` enforces that every `start_as_current_span` and `set_attribute` call references a registered constant.

### Span Types

| Span | Description |
|------|-------------|
| `decision_episode` | Root span for a sealed decision episode |
| `phase.{name}` | Child span per phase (context, plan, act, verify) |
| `drift_event` | Drift detection event |
| `coherence_evaluation` | Coherence scoring event |
| `tool_call` | Individual tool invocation within a phase |
| `llm.completion` | LLM API call with token tracking |
| `connector.{name}.{op}` | Auto-instrumented connector operation |

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sigma.episodes.total` | Counter | Total decision episodes exported |
| `sigma.episode.latency_ms` | Histogram | End-to-end episode latency |
| `sigma.drift.total` | Counter | Total drift events |
| `sigma.coherence.score` | Gauge | Latest coherence score (0-100) |
| `sigma.tool.latency_ms` | Histogram | Per-tool-call latency |
| `sigma.llm.latency_ms` | Histogram | Per-LLM-call latency |
| `sigma.llm.tokens.total` | Counter | Total LLM tokens consumed |

## Connector Auto-Instrumentation

`src/adapters/otel/instrumentation.py` provides two mechanisms:

**`@traced` decorator** — wraps any method in an OTel span:
```python
from adapters.otel.instrumentation import traced

class SharePointConnector:
    @traced("sharepoint", operation="list_items")
    def list_items(self, site_id: str) -> list:
        ...
```

**`InstrumentedConnector` mixin** — auto-wraps all public methods:
```python
from adapters.otel.instrumentation import InstrumentedConnector

class SnowflakeConnector(InstrumentedConnector):
    connector_name = "snowflake"
    def query(self, sql: str): ...  # automatically instrumented
```

## W3C Trace Context Propagation

```python
from adapters.otel.instrumentation import inject_trace_context, extract_trace_context

# Outbound: inject traceparent into HTTP headers
headers = inject_trace_context({"Authorization": "Bearer ..."})

# Inbound: extract traceparent from incoming request
ctx = extract_trace_context(request.headers)
```

## Related Pages

- [Degrade Ladder](Degrade-Ladder) — degradation triggers
- [Runtime Flow](Runtime-Flow) — where telemetry is emitted
- [SLOs and Metrics](SLOs-and-Metrics) — metric targets
