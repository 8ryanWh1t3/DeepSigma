# Palantir Foundry Integration

> Foundry remains Foundry; OVERWATCH governs calls into it. The VantageAdapter is one adapter — not the core.

## Overview

DeepSigma integrates with Palantir Foundry through the [DecisionSurface](DecisionSurface) runtime layer. The architecture is deliberately adapter-based: the core claim-event evaluation engine is portable and environment-agnostic, while the `VantageAdapter` handles Foundry-specific storage and retrieval.

```
Core Engine (severity, seal_and_hash, memory_graph)
        |
  DecisionSurface Runtime  (ingest / evaluate / seal)
        |
  SurfaceAdapter ABC  (8 abstract methods)
        |
   +-----------+-----------+
   |           |           |
Notebook    CLI       VantageAdapter
(in-memory) (+ JSON)   (Foundry/Vantage)
```

**Key principle:** Foundry maintains its own autonomy. OVERWATCH governs the calls into it — not the other way around.

## Current Status

The `VantageAdapter` is an **honest stub**. All 8 methods raise `NotImplementedError` with a roadmap reference. This is intentional — it defines the contract that a real Foundry integration must fulfill, backed by 11 contract tests that verify the interface.

**Package:** `src/core/decision_surface/vantage_adapter.py`

```python
from core.decision_surface import DecisionSurface

ds = DecisionSurface.from_surface("vantage")
# All operations raise NotImplementedError until Foundry SDK integration
```

## Adapter Interface

The VantageAdapter must implement all 8 `SurfaceAdapter` methods:

| Method | Purpose | Foundry Mapping |
|--------|---------|-----------------|
| `ingest_claims(claims)` | Store claims | Write to Foundry dataset or ontology objects |
| `ingest_events(events)` | Store events | Write Action Type instances |
| `get_claims()` | Retrieve claims | Query ontology objects (type=Claim) |
| `get_events()` | Retrieve events | Query Action Type instances |
| `get_evidence()` | Retrieve evidence | Build from claim/event matches |
| `store_drift_signals(signals)` | Persist drift detections | Write to drift tracking dataset |
| `store_patches(patches)` | Persist patch recommendations | Write to patch dataset |
| `store_evaluation_result(result)` | Persist evaluation summary | Write to evaluation dataset |

## Data Model Mapping

### Object Types

| Foundry Object Type | Envelope record_type | Notes |
|---------------------|---------------------|-------|
| Ontology Object | `Entity` | Domain entities (customers, assets, cases) |
| Dataset Row | `Claim` or `Metric` | Analytical outputs, derived facts |
| Action Type instance | `Event` | Action executions, workflow triggers |
| Media Reference | `Document` | Attachments, reports, exported artifacts |

### Field Mapping

| Foundry field | Envelope field | Transform |
|---------------|---------------|-----------|
| `objectRid` | `record_id` | `uuid_from_hash('palantir', objectRid)` |
| `objectTypeRid` | `record_type` | Map via object type table |
| `__createdTimestamp` | `created_at` | ISO-8601 from epoch ms |
| `__updatedTimestamp` | `observed_at` | ISO-8601 from epoch ms |
| `__createdBy` | `source.actor.id` | Foundry user RID via directory API |
| `properties.*` | `content` | Flatten property bag; preserve property names |
| `__primaryKey` | `content.entity_id` | Business key |
| Link types | `links[]` | Foundry link types map to envelope edge types |

### Link Types

| Foundry link type | Envelope rel | Direction |
|-------------------|-------------|-----------|
| `relatedTo` | `supports` | Forward |
| `derivedFrom` | `derived_from` | Forward |
| `partOf` | `part_of` | Forward |
| `supersededBy` | `supersedes` | Reverse (flip direction) |
| `contradicts` | `contradicts` | Forward |

## Ingestion Strategy

1. **Ontology sync** — Foundry Ontology SDK, list objects by type with pagination
2. **Incremental** — filter by `__updatedTimestamp > last_sync_ts` for delta loads
3. **Transform** — apply field mapping, resolve user RIDs, flatten properties
4. **Link resolution** — query linked objects and generate `links[]` array
5. **Validate** — run against `canonical_record.schema.json`
6. **Ingest** — write to canonical store

## Provenance

Foundry records carry strong provenance through dataset lineage:

```json
{
  "provenance": {
    "chain": [
      {"type": "source", "ref": "foundry://<enrollment>/<objectTypeRid>/<objectRid>"},
      {"type": "evidence", "ref": "<dataset_rid>", "method": "foundry_transform"}
    ]
  }
}
```

## Confidence Scoring

| Data Source | Confidence |
|-------------|-----------|
| Source-of-truth datasets | 0.95 |
| Derived/computed datasets | 0.80 |
| User-submitted data | 0.60 |

## Integration Patterns

Three core patterns govern how OVERWATCH interacts with Foundry:

1. **Feature fetch wrapper** — returns `{value, capturedAt, sourceRef}` so every read has provenance
2. **Action adapter** — requires a Safe Action Contract before any Foundry write
3. **Verifier** — reads authoritative ontology state after write to confirm postconditions

## Permissions

Requires a Foundry service user with:
- `ontology:read` — query ontology objects and link types
- `datasets:read` — read dataset rows for ingestion

## Connector Profile

| Property | Value |
|----------|-------|
| Transport | HTTPS REST |
| Auth | OAuth |
| MCP Tools | -- (planned) |
| Exhaust | foundry adapter |

## Tests

- `tests/test_vantage_adapter_contract.py` — 11 tests verifying all 8 methods raise `NotImplementedError` and adapter properties (surface_name, isinstance, factory)

## Roadmap

Full Foundry SDK integration is deferred to v2.1.1 "Institutional Expansion". The current stub + contract tests define the exact interface a real implementation must satisfy. See [DecisionSurface](DecisionSurface) for the adapter authoring guide.

## Related Pages

- [DecisionSurface](DecisionSurface) — portable runtime and adapter ABC
- [Integrations](Integrations) — all connector targets
- [Event Contracts](Event-Contracts) — routing table and event declarations
- [AuthorityOps](AuthorityOps) — authority enforcement for Foundry actions
