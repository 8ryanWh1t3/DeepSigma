# JRM Pipeline

> Log-agnostic Judgment Refinement Module — ingest external telemetry, normalize, run coherence pipeline, output JRM-X packets.

## Overview

JRM ingests external log sources (Suricata EVE, Snort fast.log, Copilot agent logs) through format-specific adapters, normalizes them into `JRMEvent` records, runs a 5-stage coherence pipeline, and outputs standardized JRM-X packet zips.

**Modules**:
- `src/core/jrm/adapters/` — lossless log parsers
- `src/core/jrm/pipeline/` — 5-stage coherence pipeline
- `src/core/jrm/packet/` — rolling packet builder
- `src/core/jrm/cli.py` — CLI commands
- `src/core/jrm/hooks/` — extension registries

**Schemas**:
- `src/core/schemas/jrm/jrm_core.schema.json` — normalized event schema
- `src/core/schemas/jrm/jrm_packet.schema.json` — packet manifest schema

## Adapters

Three built-in adapters with pluggable registry:

| Adapter | Format | Event Types | Key Extraction |
|---------|--------|-------------|----------------|
| `suricata_eve` | EVE JSON lines | alert, dns, http, flow, tls, fileinfo | signature_id, rev, severity, flow_id, src/dst |
| `snort_fastlog` | `[GID:SID:REV]` text | alerts | GID, SID, REV, priority, classification |
| `copilot_agent` | JSONL | prompt, tool_call, response, guardrail | agent, target, confidence, guardrail_flags |

**Lossless contract**: malformed lines become `MALFORMED` event type with raw bytes preserved. Every event gets a `sha256:<hex>` evidence hash.

Register custom adapters:

```python
from core.jrm.adapters.registry import register_adapter, get_adapter

register_adapter("my_format", MyAdapter)
adapter = get_adapter("my_format")
```

## Pipeline Stages

```
JRMEvent[] → Truth → Reasoning → Drift → Patch → MemoryGraph → PipelineResult
```

| Stage | Class | Purpose | Output |
|-------|-------|---------|--------|
| Truth | `TruthStage` | Cluster events into claims by (source, signature) | Claims + truth_snapshot |
| Reasoning | `ReasoningStage` | Classify events into decision lanes | ReasoningResults + DLR entries |
| Drift | `DriftStage` | Detect local coherence drift | DriftDetections + DS entries |
| Patch | `PatchStage` | Create rev++ patch records | PatchRecords with lineage |
| Memory Graph | `MemoryGraphStage` | Build provenance graph + canon postures | MG delta + canon entries |

### Decision Lanes

| Lane | Trigger | Action |
|------|---------|--------|
| `REQUIRE_REVIEW` | critical/high + confidence >= 0.8 | Human review required |
| `QUEUE_PATCH` | high + confidence < 0.8 | Auto-queue for patching |
| `NOTIFY` | medium severity | Alert operator |
| `LOG_ONLY` | low/info severity | Silent record |

### Drift Types

| Type | Detection | Threshold |
|------|-----------|-----------|
| `FP_SPIKE` | Same signature, high count, low avg confidence | count >= 10 AND avg_conf < 0.7 |
| `MISSING_MAPPING` | Events with no corresponding claim | Any unclaimed event type |
| `STALE_LOGIC` | Conflicting signature revisions in same window | rev differs for same sig_id |
| `ASSUMPTION_EXPIRED` | Assumptions past half-life | "expired" keyword in assumptions |

## JRM-X Packet Format

Each packet is a zip containing 7 files:

| File | Content |
|------|---------|
| `truth_snapshot.json` | Sensor summary, severity histogram, top signatures |
| `authority_slice.json` | Environment authority context |
| `decision_lineage.jsonl` | Per-event decision lane + why_bullets |
| `drift_signal.jsonl` | Detected drift events |
| `memory_graph.json` | Nodes/edges added (evidence, claim, drift, patch) |
| `canon_entry.json` | Current posture per signature |
| `manifest.json` | Packet metadata + SHA-256 per file |

**Rolling thresholds**: 50,000 events OR 25 MB zip size triggers auto-flush to next part.
**Naming**: `JRM_X_PACKET_<ENV>_<YYYYMMDDTHHMMSS>_<YYYYMMDDTHHMMSS>_partNN`

## CLI

```bash
# Normalize logs via adapter
coherence jrm ingest --adapter suricata_eve --in eve.json --out normalized.ndjson

# Run pipeline and produce packets
coherence jrm run --in normalized.ndjson --env SOC_EAST --packet-out /tmp/packets/

# Validate packet structure + hashes
coherence jrm validate /tmp/packets/*.zip

# List available adapters
coherence jrm adapters [--json]
```

## Extension Hooks

Four registries for enterprise and custom extensions:

| Registry | Purpose |
|----------|---------|
| `register_drift_detector(name, cls)` | Custom drift detection logic |
| `register_packet_validator(name, fn)` | Custom packet validation rules |
| `register_stream_connector(name, cls)` | Custom stream sources |
| `register_cli_hook(fn)` | Enterprise CLI subcommand registration |

## Related Pages

- [JRM Federation](JRM-Federation) — cross-environment gate, hub, advisory
- [Event Contracts](Event-Contracts) — routing table and function declarations
- [FEEDS Pipeline](FEEDS-Pipeline) — event-driven pub/sub
- [Drift -> Patch](Drift-to-Patch) — drift lifecycle
