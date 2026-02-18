# MCP Integration (Scaffold)

MCP is the tool transport standard.
Σ OVERWATCH / RAL is the autonomy governor.

## Recommended pattern: OVERWATCH as an MCP server
Expose these tools:
- `overwatch.submit_task`
- `overwatch.tool_execute`
- `overwatch.action_dispatch`
- `overwatch.verify_run`
- `overwatch.episode_seal`
- `overwatch.drift_emit`

## Scaffold assets
- `adapters/mcp/mcp_server_scaffold.py`
- `adapters/mcp/tool_catalog.json`
- `examples/mcp/mcp_client_messages.jsonl`

## Runnable Cookbook

For a step-by-step runnable example with expected output, verification, and failure modes:

→ [cookbook/mcp/hello_deepsigma/README.md](../../cookbook/mcp/hello_deepsigma/README.md)
