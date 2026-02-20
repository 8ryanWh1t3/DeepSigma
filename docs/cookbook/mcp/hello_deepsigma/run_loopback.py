#!/usr/bin/env python3
"""MCP loopback runner — sends the full sample_messages.jsonl sequence through
the MCP scaffold via subprocess and verifies every response.

Usage:
    python cookbook/mcp/hello_deepsigma/run_loopback.py

Prerequisites:
    pip install -e .   (from repo root)
    Python 3.10+

No external dependencies — uses stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO_ROOT / "adapters" / "mcp" / "mcp_server_scaffold.py"
MESSAGES_FILE = Path(__file__).parent / "sample_messages.jsonl"


def send_message(proc: subprocess.Popen, message: dict) -> dict:
    """Write one JSON-RPC request and read one response."""
    line = json.dumps(message) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    return json.loads(response_line)


def main() -> None:
    print("=== MCP Loopback: Hello DeepSigma ===\n")

    # Load sample messages (raw lines — we'll substitute session_id)
    raw_lines = [
        line.strip()
        for line in MESSAGES_FILE.read_text().splitlines()
        if line.strip()
    ]

    # Start the scaffold server as a subprocess
    proc = subprocess.Popen(
        [sys.executable, str(SCAFFOLD)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(REPO_ROOT),
    )

    session_id: str = ""
    errors: list[str] = []

    try:
        for raw_line in raw_lines:
            # Substitute the session_id placeholder once we have one
            if session_id:
                raw_line = raw_line.replace("__SESSION_ID__", session_id)

            request = json.loads(raw_line)
            response = send_message(proc, request)

            method = request.get("method", "")
            params = request.get("params", {})
            tool_name = params.get("name", method)

            print(f"[{request['id']}] {tool_name}")

            if "error" in response:
                msg = f"  ERROR: {response['error']}"
                print(msg)
                errors.append(msg)
                continue

            result = response.get("result", {})

            # Pretty-print key result fields
            if tool_name == "tools/list":
                names = [t["name"] for t in result.get("tools", [])]
                print(f"  → tools: {', '.join(names)}")

            elif tool_name == "overwatch.submit_task":
                session_id = result.get("session_id", "")
                print(f"  → session_id: {session_id}")

            elif tool_name == "overwatch.tool_execute":
                print(f"  → result tool: {result.get('result', {}).get('tool')}")
                print(f"  → capturedAt: {result.get('capturedAt')}")

            elif tool_name == "overwatch.action_dispatch":
                print(f"  → ack: {result.get('ack')}")

            elif tool_name == "overwatch.verify_run":
                print(f"  → result: {result.get('result')}")

            elif tool_name == "overwatch.episode_seal":
                sealed = result.get("sealed", {})
                seal = sealed.get("seal", {})
                print(f"  → episodeId: {sealed.get('episodeId')}")
                print(f"  → sealedAt: {seal.get('sealedAt')}")
                print(f"  → sealHash: {seal.get('sealHash')}")

            elif tool_name == "overwatch.drift_emit":
                print(f"  → ok: {result.get('ok')}")

            print()

    finally:
        proc.stdin.close()
        proc.wait(timeout=5)

    if errors:
        print(f"=== FAIL: {len(errors)} error(s) encountered ===")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("=== PASS: All messages returned valid jsonrpc responses ===")


if __name__ == "__main__":
    main()
