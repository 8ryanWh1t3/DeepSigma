# MCP Server — Production Guide

The Sigma OVERWATCH MCP server implements the [Model Context Protocol](https://modelcontextprotocol.io/) (v2024-11-05) as a JSON-RPC stdio server. MCP clients like Claude Desktop launch it as a subprocess and pipe JSON-RPC over stdin/stdout.

## Architecture

```
┌─────────────┐    stdin/stdout     ┌──────────────────────────────────┐
│ MCP Client  │ ◄── JSON-RPC ────► │  mcp_server_scaffold.py          │
│ (Claude     │                     │                                  │
│  Desktop,   │                     │  ┌──────────┐  ┌──────────────┐ │
│  VS Code,   │                     │  │ Auth     │  │ Rate Limiter │ │
│  etc.)      │                     │  └──────────┘  └──────────────┘ │
└─────────────┘                     │  ┌─────────────────────────────┐ │
                                    │  │ Tool Router (29 tools)      │ │
                                    │  │  overwatch.* (6)            │ │
                                    │  │  iris.* (2)                 │ │
                                    │  │  coherence.* (5)  ← NEW    │ │
                                    │  │  sharepoint.* (3)           │ │
                                    │  │  dataverse.* (3)            │ │
                                    │  │  asksage.* (4)              │ │
                                    │  │  cortex.* (2)               │ │
                                    │  │  snowflake.* (3)            │ │
                                    │  │  golden_path.run (1)        │ │
                                    │  └─────────────────────────────┘ │
                                    │  ┌──────────┐  ┌──────────────┐ │
                                    │  │Resources │  │ Prompts      │ │
                                    │  └──────────┘  └──────────────┘ │
                                    └──────────────────────────────────┘
```

## Tool Catalog (29 tools)

### Coherence Tools (new in v1.0.0)

| Tool | Description |
|------|-------------|
| `coherence.query_credibility_index` | Score the pipeline and return credibility index, grade, dimensional breakdown |
| `coherence.list_drift_signals` | List drift signal buckets with optional severity filter and limit |
| `coherence.get_episode` | Retrieve a decision episode by ID with Memory Graph provenance |
| `coherence.apply_patch` | Apply a drift patch to the Memory Graph |
| `coherence.seal_decision` | Seal a decision episode and write a DLR entry |

### OVERWATCH Tools

| Tool | Description |
|------|-------------|
| `overwatch.submit_task` | Start a supervised decision episode |
| `overwatch.tool_execute` | Execute a governed tool call |
| `overwatch.action_dispatch` | Dispatch a state-changing action |
| `overwatch.verify_run` | Run a verifier (read-after-write) |
| `overwatch.episode_seal` | Seal the DecisionEpisode |
| `overwatch.drift_emit` | Emit a drift event |

### IRIS Tools

| Tool | Description |
|------|-------------|
| `iris.query` | Query the IRIS resolution engine (WHY, WHAT_CHANGED, WHAT_DRIFTED, RECALL, STATUS) |
| `iris.reload` | Reload the coherence pipeline from disk |

### Connector Tools

SharePoint (3), Dataverse (3), AskSage (4), Cortex (2), Snowflake (3), Golden Path (1) — see `tool_catalog.json` for full schemas.

## Authentication

API key authentication is **optional**. When enabled, clients must pass a valid API key during `initialize`.

### Setup

```bash
# Set comma-separated list of valid API keys
export MCP_API_KEYS="key-prod-abc123,key-dev-xyz789"
```

### Protocol

1. Client sends `initialize` with `apiKey` in params:
   ```json
   {"jsonrpc":"2.0","method":"initialize","id":1,"params":{"apiKey":"key-prod-abc123"}}
   ```
2. Server validates the key and returns a `sessionId`
3. All subsequent `tools/call` requests are checked against authenticated sessions

When `MCP_API_KEYS` is not set, auth is **disabled** (backward compatible for local dev).

## Rate Limiting

Per-client sliding window rate limiter protects against runaway loops.

- **Default:** 60 requests/minute per session
- **Configure:** `export MCP_RATE_LIMIT=120`
- **Error code:** `-32003` when rate exceeded

## Docker

### Build

```bash
docker build -f Dockerfile.mcp -t deepsigma-mcp .
```

### Run

```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run --rm -i \
  -v /path/to/data:/app/data \
  deepsigma-mcp
```

### With Authentication

```bash
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"apiKey":"my-key"}}' | \
  docker run --rm -i \
  -e MCP_API_KEYS="my-key" \
  -v /path/to/data:/app/data \
  deepsigma-mcp
```

## Claude Desktop Configuration

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "deepsigma": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "/path/to/data:/app/data",
        "-e", "MCP_API_KEYS=your-key",
        "ghcr.io/8ryanwh1t3/deepsigma-mcp"
      ]
    }
  }
}
```

## Resilience

All connector tools (SharePoint, Dataverse, AskSage, Cortex, Snowflake, Golden Path) are protected by:

- **Circuit breakers** — 5 failures trip the breaker, 60s cooldown, half-open probe
- **Retry with backoff** — 3 attempts, 0.5s base delay, exponential backoff
- **Transient detection** — Only retries HTTP 429/502/503, timeouts, rate limits

See `adapters/mcp/resilience.py` for implementation details.

## Resources & Prompts

The server also exposes MCP resources and prompts:

- **Resources:** Episodes, drift events, schemas, coherence stats
- **Prompts:** `assemble_context`, `trace_decision`, `check_contradictions`

See `resource_catalog.json` and `prompt_catalog.json` for full definitions.

## Testing

```bash
# All MCP tests
pytest tests/test_mcp_production.py tests/test_mcp_iris.py tests/test_mcp_resources.py tests/test_mcp_resilience.py -v

# Loopback smoke test
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python adapters/mcp/mcp_server_scaffold.py
```
