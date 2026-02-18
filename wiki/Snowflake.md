# Snowflake

Dual-mode connector for Snowflake: **Cortex AI** for LLM completions and embeddings, plus **warehouse SQL** for structured query and table sync.

## Overview

Snowflake serves two roles in the RAL stack:

1. **Cortex AI** -- LLM completions (`cortex.complete`) and embedding generation (`cortex.embed`) via the Cortex REST API.
2. **Warehouse** -- SQL query execution (`snowflake.query`), table listing (`snowflake.tables`), and bidirectional table sync (`snowflake.sync`).

Both modes share a single auth layer and route all activity through the Exhaust Inbox.

## Auth Options

| Method | Use Case | Config Key |
|--------|----------|------------|
| JWT Keypair | Service accounts, CI/CD | `auth.keypair` |
| OAuth | Interactive / SSO | `auth.oauth` |
| PAT (Personal Access Token) | Developer local | `auth.pat` |

```python
from deepsigma.adapters.snowflake import SnowflakeConnector

conn = SnowflakeConnector(
    account="org-acct",
    auth_method="keypair",
    private_key_path="/secrets/rsa_key.p8",
)
```

## Cortex AI Mode

Cortex endpoints are accessed via the Snowflake REST API under `/api/v2/cortex`.

```python
# LLM completion
result = conn.cortex_complete(
    model="snowflake-arctic",
    prompt="Classify this alert...",
    dte_id="dte-xyz-456",
)

# Embedding
vec = conn.cortex_embed(
    model="e5-base-v2",
    text="network intrusion detected",
)
```

Each call is DTE-gated (budget, TTL, scope) before execution.

## Warehouse Mode

Standard SQL query execution against any warehouse the service account can access.

```python
rows = conn.query("SELECT * FROM threat_intel.iocs LIMIT 100")
tables = conn.list_tables(schema="threat_intel")
conn.sync(source_table="stg.raw_events", target="canonical.episodes")
```

`snowflake.sync` performs an incremental merge using a `_updated_at` watermark column.

## Exhaust Adapter

Both Cortex and warehouse operations emit `EpisodeEvent` records:

```python
adapter = ExhaustAdapter(source="snowflake")
# Fields: mode (cortex|warehouse), operation, latency_ms,
#         rows_affected, token_count, cost_usd, dte_id
```

## MCP Tools

| Tool | Mode | Description |
|------|------|-------------|
| `cortex.complete` | Cortex | DTE-gated LLM completion |
| `cortex.embed` | Cortex | Generate embeddings |
| `snowflake.query` | Warehouse | Execute a SQL query |
| `snowflake.tables` | Warehouse | List tables/views in a schema |
| `snowflake.sync` | Warehouse | Incremental table sync |

### Example: MCP completion call

```json
{
  "tool": "cortex.complete",
  "arguments": {
    "model": "snowflake-arctic",
    "prompt": "Summarize IOC findings",
    "dte_id": "dte-xyz-456",
    "max_tokens": 1024
  }
}
```

## Configuration

```yaml
# config/snowflake.yaml
snowflake:
  account: org-acct
  auth:
    method: keypair
    private_key_env: SNOWFLAKE_PRIVATE_KEY
  cortex:
    default_model: snowflake-arctic
    embed_model: e5-base-v2
  warehouse:
    default_wh: COMPUTE_WH
    sync_watermark: _updated_at
  exhaust:
    adapter: snowflake
```

## Related

- [Integrations](Integrations.md)
- [MCP](MCP.md)
- [Exhaust Inbox](Exhaust-Inbox.md)
- [AskSage](AskSage.md)
