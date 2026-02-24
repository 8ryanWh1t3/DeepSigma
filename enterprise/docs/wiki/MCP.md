# MCP

MCP is the transport standard for tool calling.
RAL uses MCP in two modes:

## A) OVERWATCH as MCP server (recommended)
Expose Overwatch primitives as MCP tools.

## B) MCP gateway mode
Proxy calls to other MCP servers and enforce:
- budgets, TTL, verification, safe action contracts, sealing

Scaffold:
- `adapters/mcp/`
