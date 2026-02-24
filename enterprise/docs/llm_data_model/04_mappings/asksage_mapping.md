# AskSage → LLM Data Model Mapping

## Overview

AskSage query/response pairs and training events map into canonical records.  This document covers ingestion from the AskSage Server and User APIs.

## Object type mapping

| AskSage Object | Envelope record_type | Notes |
|---|---|---|
| Query response | `Event` | Each query→response pair is a decision event |
| Training submission | `Document` | Content added to a dataset |
| Model listing | n/a | Metadata only — not ingested |
| Prompt history log | `Event` | Historical query record |

## Field mapping

| AskSage field | Envelope field | Transform |
|---|---|---|
| query prompt | `content.prompt` | Passthrough |
| response text | `content.response` | Passthrough |
| model used | `content.model` | Passthrough |
| dataset | `labels.tags[]` | `dataset:<name>` |
| persona | `labels.tags[]` | `persona:<name>` |
| timestamp | `created_at` / `observed_at` | ISO-8601 |
| n/a | `record_id` | `uuid_from_hash('asksage', sha256(prompt + model + ts)[:16])` |
| n/a | `record_type` | `Event` (query) or `Document` (training) |
| n/a | `provenance` | `asksage://<model>/<query_hash>` |
| n/a | `confidence.score` | `0.70` (LLM-generated content) |
| n/a | `source.actor.type` | `system` (AskSage platform) |

## Ingestion strategy

1. **Query capture** — wrap `AskSageConnector.query()` via `AskSageExhaustAdapter`.
2. **Event pair** — each query produces a prompt event + response event + metric event.
3. **Transform** — apply field mapping, generate deterministic record_id.
4. **Validate** — run against `canonical_record.schema.json`.
5. **Ingest** — write to canonical store via exhaust endpoint.

## Provenance

- `provenance.chain[0]`: `{type: "source", ref: "asksage://<model>/<query_hash>"}`
- For training events: `{type: "source", ref: "asksage://train/<dataset>/<content_hash>"}`

## Confidence scoring

- All AskSage outputs: `confidence.score = 0.70` (LLM-generated, not system-of-record)

## Permissions

Requires an AskSage API key with access to the Server API (`/server/*`) and User API (`/user/*`).
