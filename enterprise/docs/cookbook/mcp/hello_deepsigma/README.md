# Cookbook: MCP — Hello DeepSigma

**Adapter:** `adapters/mcp/mcp_server_scaffold.py`
**Status:** Scaffold — JSON-RPC 2.0 over stdio. Full MCP handshake (capabilities negotiation) is not yet implemented; the scaffold is ready for integration with any MCP host that speaks JSON-RPC over stdio.

This recipe shows:
1. What the MCP contract looks like (request/response shapes)
2. How to run a local loopback to verify the scaffold works
3. What artifacts are produced (session events, sealed episode)

---

## Prerequisites

- Python 3.10+
- DeepSigma installed: `pip install -e .` (from repo root)
- No external MCP library required — the scaffold uses stdlib only

---

## Steps

### Step 1 — Understand the contract

The scaffold exposes six tools via `tools/call`:

| Tool | Purpose |
|------|---------|
| `overwatch.submit_task` | Start a new decision session |
| `overwatch.tool_execute` | Execute a tool within the session |
| `overwatch.action_dispatch` | Dispatch an action |
| `overwatch.verify_run` | Run verification |
| `overwatch.episode_seal` | Seal the episode (finalize) |
| `overwatch.drift_emit` | Emit a drift event |

See `sample_messages.jsonl` in this directory for the full message sequence.

### Step 2 — Run the loopback script

```bash
# From repo root:
python cookbook/mcp/hello_deepsigma/run_loopback.py
```

This script sends the complete message sequence through the MCP scaffold via subprocess and prints each request → response pair.

### Step 3 — Run the scaffold manually (stdin/stdout)

You can also drive the scaffold by hand with `echo` or from another process:

```bash
# List available tools
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python adapters/mcp/mcp_server_scaffold.py

# Submit a task (start a session)
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"overwatch.submit_task","arguments":{"decisionType":"LoanApproval"}}}' \
  | python adapters/mcp/mcp_server_scaffold.py
```

---

## Expected Output

Running `run_loopback.py` should produce output similar to:

```
=== MCP Loopback: Hello DeepSigma ===

[1] tools/list
  → tools: overwatch.submit_task, overwatch.tool_execute, overwatch.action_dispatch,
           overwatch.verify_run, overwatch.episode_seal, overwatch.drift_emit

[2] overwatch.submit_task (decisionType=LoanApproval)
  → session_id: sess_a1b2c3d4e5f6

[3] overwatch.tool_execute (tool=credit_check)
  → result: {echo: {...}, tool: credit_check}
  → capturedAt: 2026-...Z

[4] overwatch.action_dispatch
  → ack: {status: accepted}

[5] overwatch.verify_run (method=schema_check)
  → result: pass

[6] overwatch.episode_seal
  → sealed: {seal: {sealedAt: ..., sealHash: scaffold}}

[7] overwatch.drift_emit
  → ok: True

=== PASS: All 7 messages returned jsonrpc responses ===
```

---

## Verification

After running the loopback:

1. Every response has `"jsonrpc": "2.0"` — confirms JSON-RPC framing is correct.
2. The `episode_seal` response includes `seal.sealedAt` — confirms the episode was sealed with a timestamp.
3. No `"error"` keys appear — confirms all tool names and session IDs resolved correctly.

If the loopback script prints `=== PASS ===`, the MCP scaffold is operating correctly.

---

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `FileNotFoundError: tool_catalog.json` | Script not run from repo root | `cd /path/to/DeepSigma` first |
| `json.decoder.JSONDecodeError` | Malformed request JSON | Check `sample_messages.jsonl` for syntax |
| `"error": {"code": -32000, "message": "Unknown session_id"}` | Session ID from `submit_task` not reused in subsequent calls | The loopback script handles this automatically |
| `ModuleNotFoundError: core` | Package not installed | `pip install -e .` from repo root |

---

## Connecting to a Real MCP Host

To connect the scaffold to a real MCP host (e.g., Claude Desktop, Continue.dev):

1. Configure the host to spawn: `python /path/to/DeepSigma/adapters/mcp/mcp_server_scaffold.py`
2. Communication is via stdin/stdout (JSON-RPC lines)
3. The scaffold will respond to `tools/list` and `tools/call` requests
4. Implement your host-side session management to chain `session_id` through the calls

> **Note:** Full MCP capabilities negotiation (the `initialize` / `initialized` handshake) is not yet implemented. The scaffold skips this phase and responds to tool calls directly.
