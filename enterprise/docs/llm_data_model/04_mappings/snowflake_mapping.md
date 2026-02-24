# Snowflake → LLM Data Model Mapping

## Overview

Snowflake provides two ingestion paths: **Cortex AI** (LLM completions and embeddings) and **Data Warehouse** (SQL query results).  This document covers both.

## Cortex AI mapping

### Object type mapping

| Cortex Operation | Envelope record_type | Notes |
|---|---|---|
| Complete (chat) | `Event` | LLM completion request/response pair |
| Embed | n/a | Embeddings are metadata — not directly ingested as records |

### Field mapping

| Cortex field | Envelope field | Transform |
|---|---|---|
| response text | `content.response` | Assemble from SSE `data:` chunks |
| model | `content.model` | Passthrough |
| usage.prompt_tokens | `content.prompt_tokens` | Passthrough |
| usage.completion_tokens | `content.completion_tokens` | Passthrough |
| n/a | `record_id` | `uuid_from_hash('cortex', request_id)` |
| n/a | `record_type` | `Event` |
| n/a | `provenance` | `cortex://<account>/<model>/<request_id>` |
| n/a | `confidence.score` | `0.70` (LLM-generated) |

## Data Warehouse mapping

### Object type mapping

| SQL Result Type | Envelope record_type | Notes |
|---|---|---|
| Dimensional table row | `Entity` | Tables with name/account/customer columns |
| Metric/measurement row | `Metric` | Tables with value/score/measurement columns |
| Analytical result row | `Claim` | Default for derived/computed data |

### Field mapping

| SQL field | Envelope field | Transform |
|---|---|---|
| Primary key column | `record_id` | `uuid_from_hash('snowflake', f"{db}.{schema}.{table}.{pk}")` |
| Row data | `content` | Flatten row dict |
| CREATED_AT column | `created_at` | ISO-8601 |
| UPDATED_AT column | `observed_at` | ISO-8601 |
| n/a | `provenance` | `snowflake://<account>/<db>.<schema>.<table>/<pk>` |
| n/a | `confidence.score` | `0.90` (warehouse data = high quality) |
| n/a | `ttl` | `86400000` (24h default) |

## Ingestion strategy

### Cortex AI
1. **Wrap** — use `CortexExhaustAdapter` around `CortexConnector.complete()`.
2. **Event triple** — each completion produces prompt + response + metric events.
3. **Validate** — run against `canonical_record.schema.json`.

### Data Warehouse
1. **Query** — use `SnowflakeWarehouseConnector.sync_table()` for incremental loads.
2. **Transform** — `to_canonical()` applies field mapping, generates UUIDs.
3. **Validate** — run against `canonical_record.schema.json`.
4. **Ingest** — write to canonical store.

## Authentication

Three methods supported (in priority order):

1. **JWT (Keypair)** — `SNOWFLAKE_PRIVATE_KEY_PATH` + `SNOWFLAKE_USER`; requires `cryptography` package.
2. **OAuth** — `SNOWFLAKE_TOKEN` (OAuth access token).
3. **PAT** — `SNOWFLAKE_TOKEN` starting with `ver:` (Programmatic Access Token).

Headers: `Authorization: Bearer <token>`, `X-Snowflake-Authorization-Token-Type: <KEYPAIR_JWT|OAUTH|PROGRAMMATIC_ACCESS_TOKEN>`.

## Permissions

- Cortex: Requires access to the Cortex AI functions (USAGE on database with Cortex enabled).
- Warehouse: Requires SELECT on target tables, USAGE on warehouse.
