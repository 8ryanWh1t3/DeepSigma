# Node Types

In the LLM Data Model knowledge graph, every canonical record is a **node**.  The `record_type` field determines the node type.

## Core node types

| Node Type | Description | Lifecycle | Typical TTL |
|---|---|---|---|
| `Claim` | An assertion with evidence and confidence.  The fundamental unit of AI-readable knowledge. | Created → sealed → may expire via TTL → may be superseded by a newer claim | Short (minutes to hours) |
| `DecisionEpisode` | A sealed, immutable record of a decision.  Maps 1:1 to a RAL episode. | Created → sealed → permanent.  Never expires, never patched (append-only patch_log). | Perpetual (0) |
| `Event` | Something that happened at a point in time.  Drift events, triggers, notifications. | Created → sealed.  May expire if operational relevance fades. | Medium (hours to days) |
| `Document` | A policy, DTE definition, procedure, or reference document. | Authored → approved → sealed.  New versions supersede old ones. | Perpetual (0) |
| `Entity` | A persistent domain object: customer, service, model, endpoint. | Created → periodically refreshed via patch_log.  TTL drives refresh cadence. | Medium (24h typical) |
| `Metric` | A measured value with timestamp: latency, throughput, score. | Created → sealed.  Point-in-time measurement. | Medium (hours to days) |

## Node properties (shared)

Every node carries the full canonical envelope.  Key properties for graph operations:

| Property | Graph use |
|---|---|
| `record_id` | Node identity (primary key) |
| `record_type` | Node type / label |
| `labels.domain` | Graph partition / sub-graph |
| `confidence.score` | Edge weight input (higher confidence = stronger signal) |
| `ttl` + `observed_at` | Freshness gate — expired nodes are excluded from traversal by default |
| `links[]` | Outbound edges (see edge_types.md) |

## Type-specific content shapes

Each node type has a recommended content structure.  These are not enforced by the envelope schema but documented here for consistency:

### Claim content

Key fields: `anomaly_type`, `deviation_sigma`, `recommended_action`, plus domain-specific measurements.

### DecisionEpisode content

Mirrors the RAL episode schema: `episode_id`, `decision_type`, `actor`, `dte_ref`, `context`, `plan`, `actions`, `verification`, `outcome`, `telemetry`.

### Event content

Key fields: `event_type`, `severity`, plus type-specific details.  For drift events: `drift_type`, `recommended_patch_type`, `fingerprint`.

### Document content

Key fields: `document_type`, `title`, `version`, plus the document body or structured definition.

### Entity content

Key fields: `entity_type`, `entity_id`, `display_name`, `status`, plus domain-specific attributes.

### Metric content

Key fields: `metric_name`, `value`, `unit`, `aggregation` (point, avg, p95, p99), `window_ms`.
