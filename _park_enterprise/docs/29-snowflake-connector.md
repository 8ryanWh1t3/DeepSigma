# Snowflake Connector

Dual-mode Snowflake connector: Cortex AI (LLM completion + embeddings) and SQL Warehouse (data queries + canonical record ingestion).

The Snowflake adapter provides two connectors sharing a common auth layer. `CortexConnector` accesses Snowflake Cortex AI for LLM inference and embeddings. `SnowflakeWarehouseConnector` executes SQL via the REST API and transforms results to canonical records.

**Source:** `adapters/snowflake/cortex.py`, `adapters/snowflake/warehouse.py`, `adapters/snowflake/_auth.py`

---

## Setup

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | Yes | Account identifier (e.g. `myorg-myaccount`) |
| `SNOWFLAKE_USER` | JWT only | Username for JWT auth |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | JWT only | Path to RSA private key PEM file |
| `SNOWFLAKE_TOKEN` | OAuth/PAT only | Pre-generated OAuth or PAT token |
| `SNOWFLAKE_DATABASE` | Warehouse only | Default database |
| `SNOWFLAKE_SCHEMA` | No | Default schema (default: `PUBLIC`) |
| `SNOWFLAKE_WAREHOUSE` | Warehouse only | Compute warehouse name |

### Auth methods

| Method | Config | Notes |
|---|---|---|
| **JWT (keypair)** | `SNOWFLAKE_PRIVATE_KEY_PATH` + `SNOWFLAKE_USER` | Requires `cryptography` package. Install with `pip install 'deepsigma[snowflake]'`. Token auto-refreshes every hour. |
| **OAuth** | `SNOWFLAKE_TOKEN` | Pre-generated OAuth token. |
| **PAT** | `SNOWFLAKE_TOKEN` (starts with `ver:`) | Programmatic Access Token. Auto-detected by `ver:` prefix. |

```bash
# JWT auth
export SNOWFLAKE_ACCOUNT="myorg-myaccount"
export SNOWFLAKE_USER="MY_USER"
export SNOWFLAKE_PRIVATE_KEY_PATH="/path/to/rsa_key.p8"

# OR OAuth/PAT auth
export SNOWFLAKE_ACCOUNT="myorg-myaccount"
export SNOWFLAKE_TOKEN="your-oauth-or-pat-token"
```

---

## Cortex AI Usage

```python
from adapters.snowflake.cortex import CortexConnector

cortex = CortexConnector()

# Streaming completion (returns list of chunk strings)
chunks = cortex.complete("mistral-large", [{"role": "user", "content": "Hello"}])
print("".join(chunks))

# Synchronous completion (returns {response, model, usage})
result = cortex.complete_sync("mistral-large", [{"role": "user", "content": "Hello"}])

# Embeddings (returns {embeddings, model})
result = cortex.embed("e5-base-v2", ["text one", "text two"])
```

---

## Warehouse Usage

```python
from adapters.snowflake.warehouse import SnowflakeWarehouseConnector

wh = SnowflakeWarehouseConnector()
rows = wh.query("SELECT * FROM my_table LIMIT 10")
tables = wh.list_tables()
records = wh.to_canonical(rows, "my_table")

# Sync (full or incremental)
result = wh.sync_table("events", since="2026-02-01T00:00:00Z")
```

---

## API Reference

### `SnowflakeAuth`

| Method | Returns | Description |
|---|---|---|
| `get_headers()` | `dict` | Authorization headers with token type detection. |
| `account` | `str` | Account identifier (property). |
| `base_url` | `str` | `https://{account}.snowflakecomputing.com` (property). |

### `CortexConnector`

| Method | Returns | Description |
|---|---|---|
| `complete(model, messages, max_tokens?, temperature?, tools?)` | `list[str]` | SSE streaming completion. Returns chunks. |
| `complete_sync(model, messages, max_tokens?, temperature?)` | `dict` | Collects stream into `{response, model, usage}`. |
| `embed(model, texts)` | `dict` | Generate embeddings. Returns `{embeddings, model}`. |

### `SnowflakeWarehouseConnector`

| Method | Returns | Description |
|---|---|---|
| `query(sql)` | `list[dict]` | Execute SQL, return rows as dicts. |
| `list_tables()` | `list[dict]` | List tables in configured database/schema. |
| `get_table_schema(table)` | `list[dict]` | Describe table columns. |
| `to_canonical(rows, table_name)` | `list[dict]` | Transform rows to canonical record envelopes. |
| `sync_table(table_name, since?)` | `dict` | Sync rows. Returns `{synced, records}`. |

### Canonical record mapping (warehouse)

| Source | Canonical field | Notes |
|---|---|---|
| `ID` / `id` / `PK` | `record_id` | Hashed via `uuid_from_hash("snowflake", ...)` |
| Row content heuristic | `record_type` | `Metric` if has metric/value/score fields, `Entity` if has name/account fields, else `Claim` |
| `CREATED_AT` | `created_at` | ISO 8601 |
| `UPDATED_AT` | `observed_at` | ISO 8601 |
| *(all columns)* | `content` | Full row as dict |
| table name | `labels.tags` | As `table:{name}` |

Default confidence: `0.90`. Default TTL: `86400000` (24h).

---

## MCP Tools

| Tool | Description |
|---|---|
| `snowflake_query` | Execute SQL query against the warehouse |
| `snowflake_list_tables` | List tables in configured database/schema |
| `snowflake_describe_table` | Get column definitions for a table |
| `snowflake_sync_table` | Sync table rows to canonical records |
| `cortex_complete` | LLM completion via Cortex AI |
| `cortex_embed` | Generate embeddings via Cortex AI |

---

## Files

| File | Path |
|---|---|
| Cortex connector | `adapters/snowflake/cortex.py` |
| Warehouse connector | `adapters/snowflake/warehouse.py` |
| Auth helper | `adapters/snowflake/_auth.py` |
| Connector helpers | `adapters/_connector_helpers.py` |
| This doc | `docs/29-snowflake-connector.md` |
