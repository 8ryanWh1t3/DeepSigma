# Cookbook: OTel — Trace Drift Patch

**Adapter:** `adapters/otel/exporter.py`
**Status:** Alpha — span names and attributes may change before v1.0.

This recipe shows how to:
1. Enable console tracing with minimal environment setup
2. Export a sealed episode and a drift event as OpenTelemetry spans
3. Run the Money Demo with tracing enabled
4. Verify expected span names in console output

---

## Prerequisites

- Python 3.10+
- DeepSigma installed: `pip install -e .`
- OpenTelemetry SDK:
  ```bash
  pip install -e ".[otel]"
  # or manually:
  pip install "opentelemetry-api>=1.20.0" "opentelemetry-sdk>=1.20.0"
  ```

> **No OTel backend required for this recipe** — spans are written to stdout. See `env.example` for remote export configuration.

---

## Steps

### Step 1 — Set environment variables

```bash
# Source the example env file:
source cookbook/otel/trace_drift_patch/env.example

# Or set manually (console-only, no backend needed):
export OTEL_SERVICE_NAME="sigma-overwatch"
```

### Step 2 — Export a sealed episode

```bash
python - <<'EOF'
import sys
sys.path.insert(0, ".")
import json
from pathlib import Path
from adapters.otel.exporter import OtelExporter

exporter = OtelExporter(service_name="sigma-overwatch")

# Load a real sealed episode
episode = json.loads(
    Path("examples/episodes/01_success.json").read_text()
)

result = exporter.export_episode(episode)
print("Export result:", result)
EOF
```

### Step 3 — Export a drift event

```bash
python - <<'EOF'
import sys
sys.path.insert(0, ".")
import json
from pathlib import Path
from adapters.otel.exporter import OtelExporter

exporter = OtelExporter(service_name="sigma-overwatch")

drift = json.loads(
    Path("examples/drift/freshness_drift.json").read_text()
)

exporter.export_drift(drift)
print("Drift span emitted.")
EOF
```

### Step 4 — Run the Money Demo with tracing

```bash
# With env sourced:
source cookbook/otel/trace_drift_patch/env.example
python -m coherence_ops.examples.drift_patch_cycle
```

The drift_patch_cycle does not call OtelExporter by default, but you can integrate it:

```python
import sys
sys.path.insert(0, ".")
import json
from pathlib import Path
from adapters.otel.exporter import OtelExporter

exporter = OtelExporter(service_name="sigma-overwatch")

for ep_file in sorted(Path("examples/episodes").glob("*.json")):
    episode = json.loads(ep_file.read_text())
    exporter.export_episode(episode)
    print(f"Exported: {episode.get('episodeId')}")

for drift_file in sorted(Path("examples/drift").glob("*.json")):
    drift = json.loads(drift_file.read_text())
    exporter.export_drift(drift)
    print(f"Drift exported: {drift.get('driftId')}")
```

---

## Expected Output (Console Spans)

The `ConsoleSpanExporter` prints spans to stdout in JSON format. You should see:

```
{
    "name": "phase.context",
    "context": { "trace_id": "0x...", "span_id": "0x..." },
    "parent_id": "0x...",
    "start_time": "...",
    "end_time": "...",
    "attributes": {
        "phase.name": "context",
        "phase.duration_ms": 12
    },
    ...
}
{
    "name": "phase.plan",
    ...
}
{
    "name": "phase.act",
    ...
}
{
    "name": "phase.verify",
    ...
}
{
    "name": "decision_episode",
    "attributes": {
        "episode.id": "ep-001",
        "episode.decision_type": "LoanApproval",
        "episode.degrade_step": "none"
    },
    "status": { "status_code": "OK" },
    ...
}
```

**Expected span names per episode export:**
- `phase.context`
- `phase.plan`
- `phase.act`
- `phase.verify`
- `decision_episode` (root span, appears last due to ConsoleSpanExporter ordering)

**Expected span names per drift export:**
- `drift_event`

---

## Verification

1. Run `exporter.export_episode(episode)` — check the return value:
   ```python
   {"status": "exported", "episodeId": "ep-001", "spansCreated": 5}
   ```
2. Console shows exactly 5 span JSON blocks per episode (4 phases + root).
3. Root span `episode.decision_type` matches the episode's `decisionType` field.
4. Root span `status.status_code` is `"OK"` for successful episodes, `"ERROR"` for failed.

---

## Sending to a Remote Backend

To send spans to Jaeger, Honeycomb, Grafana Tempo, or any OTLP-compatible backend:

```bash
# Jaeger (all-in-one, local):
docker run -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one

# Set env:
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="sigma-overwatch"

# Then install OTLP exporter:
pip install opentelemetry-exporter-otlp

# Run your export script — spans will appear in Jaeger UI at http://localhost:16686
```

See `env.example` for all configurable variables.

---

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `WARNING: opentelemetry packages not installed; OtelExporter is a no-op` | OTel SDK not installed | `pip install -e ".[otel]"` |
| No spans appear in console | `OtelExporter` initialized with `endpoint=` set to a non-console value, or SDK disabled | Check `OTEL_SDK_DISABLED` is not `"true"` |
| `grpc._channel._InactiveRpcError` | OTLP endpoint set but backend not running | Start backend or unset `OTEL_EXPORTER_OTLP_ENDPOINT` for console-only mode |
| `AttributeError: NoneType` on export | `OtelExporter._tracer` is None (OTel not installed) | Check import warning at startup |
