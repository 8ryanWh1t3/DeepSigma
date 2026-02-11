# MCP Adapter (Reality Await Layer transport)

Model Context Protocol (MCP) is a *tool transport standard*.
Σ OVERWATCH / RAL is the *governor*.

**MCP + RAL = production-grade tool calling** (deadlines, TTL freshness, safe actions, verification, sealed episodes).

This directory provides a **minimal MCP server scaffold** that exposes Overwatch primitives as MCP tools.

## Modes
### A) OVERWATCH as MCP server (recommended)
Expose the following MCP tools:
- `overwatch.submit_task`
- `overwatch.tool_execute`
- `overwatch.action_dispatch`
- `overwatch.verify_run`
- `overwatch.episode_seal`
- `overwatch.drift_emit`

### B) MCP gateway mode
Keep existing MCP servers; place Overwatch in front as a policy/timing gateway.

## Quickstart (scaffold)
This scaffold is dependency-free and demonstrates the JSON-RPC shape.
It is **not** a full MCP implementation yet.

Run (stdio):
```bash
python adapters/mcp/mcp_server_scaffold.py
```

Then send JSON-RPC messages on stdin (see `examples/mcp/mcp_client_messages.jsonl`).

## Next (v0.1 target)
- Implement MCP `initialize` handshake + `tools/list` + `tools/call`
- Provide a reference client demo (LangChain + MCP)
- Add schema validation for tool inputs/outputs
