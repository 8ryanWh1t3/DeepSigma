# Palantir Foundry → LLM Data Model Mapping

## Overview

Palantir Foundry datasets and ontology objects map into canonical records.  This document covers ingestion from Foundry's Object Storage Service (OSS) and Ontology API.

## Object type mapping

| Foundry Object Type | Envelope record_type | Notes |
|---|---|---|
| Ontology Object | `Entity` | Domain entities (customers, assets, cases) |
| Dataset Row | `Claim` or `Metric` | Analytical outputs, derived facts |
| Action Type instance | `Event` | Action executions, workflow triggers |
| Media Reference | `Document` | Attachments, reports, exported artifacts |

## Field mapping

| Foundry field | Envelope field | Transform |
|---|---|---|
| `objectRid` | `record_id` | `uuid_from_hash('palantir', objectRid)` |
| `objectTypeRid` | `record_type` | Map via object type table above |
| `__createdTimestamp` | `created_at` | ISO-8601 from epoch ms |
| `__updatedTimestamp` | `observed_at` | ISO-8601 from epoch ms |
| `__createdBy` | `source.actor.id` | Foundry user RID → display name via directory API |
| `properties.*` | `content` | Flatten property bag; preserve property names as keys |
| `__primaryKey` | `content.entity_id` | Business key within the content payload |
| Link types | `links[]` | Foundry link types map to envelope edge types |

## Link type mapping

| Foundry link type | Envelope rel | Direction |
|---|---|---|
| `relatedTo` | `supports` | Forward |
| `derivedFrom` | `derived_from` | Forward |
| `partOf` | `part_of` | Forward |
| `supersededBy` | `supersedes` | Reverse (flip direction) |
| `contradicts` | `contradicts` | Forward |

## Ingestion strategy

1. **Ontology sync** — use Foundry's Ontology SDK to list objects by type with pagination.
2. **Incremental** — filter by `__updatedTimestamp > last_sync_ts` for delta loads.
3. **Transform** — apply field mapping, resolve user RIDs, flatten properties.
4. **Link resolution** — query linked objects and generate `links[]` array with target record_ids.
5. **Validate** — run against `canonical_record.schema.json`.
6. **Ingest** — write to canonical store.

## Provenance

Foundry records carry strong provenance through dataset lineage.  The connector should populate:

- `provenance.chain[0]`: `{type: "source", ref: "foundry://<enrollment>/<objectTypeRid>/<objectRid>"}`
- `provenance.chain[1]`: `{type: "evidence", ref: "<dataset_rid>", method: "foundry_transform"}` (if object was derived from a pipeline)

## Confidence scoring

- Objects from source-of-truth datasets: `confidence.score = 0.95`
- Objects from derived/computed datasets: `confidence.score = 0.80`
- Objects from user-submitted data: `confidence.score = 0.60`

## Permissions

Requires a Foundry service user with `ontology:read` and `datasets:read` grants on the target project.
