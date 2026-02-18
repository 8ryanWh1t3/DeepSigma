#!/usr/bin/env python3
"""MCP Server Scaffold (dependency-free)

This is a minimal JSON-RPC stdio server demonstrating the shape needed for MCP integration.
Not a full MCP implementation yet (handshake/capabilities are simplified).

Supported JSON-RPC methods (scaffold):
- tools/list
- tools/call

Run:
  python adapters/mcp/mcp_server_scaffold.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CATALOG = json.loads((ROOT / "adapters" / "mcp" / "tool_catalog.json").read_text(encoding="utf-8"))

# Lazy-loaded IRIS pipeline (built on first iris.query or iris.reload)
_iris_pipeline: Optional[Dict[str, Any]] = None


def _load_pipeline(data_path: str = "") -> Optional[Dict[str, Any]]:
    """Load episodes and drift from data_path, build coherence pipeline."""
    global _iris_pipeline
    data_path = data_path or os.environ.get("DATA_DIR", "/app/data")
    p = Path(data_path)
    if not p.exists():
        return None
    try:
        from coherence_ops.cli import _build_pipeline, _load_drift, _load_episodes
        from coherence_ops.iris import IRISConfig, IRISEngine

        episodes = _load_episodes(str(p)) if (p / "episodes").exists() or list(p.glob("*.json")) else []
        drift_events = _load_drift(str(p))
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )
        _iris_pipeline = {
            "engine": engine,
            "dlr": dlr, "rs": rs, "ds": ds, "mg": mg,
            "episode_count": len(episodes),
            "drift_count": len(drift_events),
        }
        return _iris_pipeline
    except Exception:
        return None

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

SESSIONS: Dict[str, Dict[str, Any]] = {}

def rpc_result(_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": _id, "result": result}

def rpc_error(_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}}

def handle_tools_list(_id: Any) -> Dict[str, Any]:
    tool_list = [{k: t[k] for k in ("name", "description", "inputSchema") if k in t} for t in CATALOG.get("tools", [])]
    return rpc_result(_id, {"tools": tool_list})

def handle_tools_call(_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not name:
        return rpc_error(_id, -32602, "Missing params.name")

    if name == "overwatch.submit_task":
        session_id = "sess_" + uuid.uuid4().hex[:12]
        SESSIONS[session_id] = {"decisionType": arguments.get("decisionType"), "startedAt": iso_now(), "events": []}
        return rpc_result(_id, {"session_id": session_id})

    if name == "overwatch.tool_execute":
        session_id = arguments.get("session_id")
        if session_id not in SESSIONS:
            return rpc_error(_id, -32000, "Unknown session_id")
        tool = arguments.get("tool")
        result = {"echo": arguments.get("input", {}), "tool": tool}
        SESSIONS[session_id]["events"].append({"type": "tool", "tool": tool, "at": iso_now()})
        return rpc_result(_id, {"result": result, "capturedAt": iso_now(), "sourceRef": f"tool://{tool}"})

    if name == "overwatch.action_dispatch":
        session_id = arguments.get("session_id")
        if session_id not in SESSIONS:
            return rpc_error(_id, -32000, "Unknown session_id")
        SESSIONS[session_id]["events"].append({"type": "action", "at": iso_now()})
        return rpc_result(_id, {"ack": {"status": "accepted"}})

    if name == "overwatch.verify_run":
        session_id = arguments.get("session_id")
        if session_id not in SESSIONS:
            return rpc_error(_id, -32000, "Unknown session_id")
        method = arguments.get("method")
        SESSIONS[session_id]["events"].append({"type": "verify", "method": method, "at": iso_now()})
        return rpc_result(_id, {"result": "pass", "details": {"method": method}})

    if name == "overwatch.episode_seal":
        session_id = arguments.get("session_id")
        if session_id not in SESSIONS:
            return rpc_error(_id, -32000, "Unknown session_id")
        episode = arguments.get("episode", {})
        episode.setdefault("seal", {})
        episode["seal"]["sealedAt"] = iso_now()
        episode["seal"]["sealHash"] = "scaffold"
        SESSIONS[session_id]["endedAt"] = iso_now()
        return rpc_result(_id, {"sealed": episode})

    if name == "overwatch.drift_emit":
        return rpc_result(_id, {"ok": True})

    if name == "iris.query":
        global _iris_pipeline
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline is None:
            return rpc_error(_id, -32000, "No data loaded. Call iris.reload first or set DATA_DIR.")
        from coherence_ops.iris import IRISQuery
        query = IRISQuery(
            query_type=arguments.get("query_type", "STATUS"),
            text=arguments.get("text", ""),
            episode_id=arguments.get("episode_id", ""),
            claim_id=arguments.get("claim_id", ""),
            decision_type=arguments.get("decision_type", ""),
        )
        response = _iris_pipeline["engine"].resolve(query)
        return rpc_result(_id, response.to_dict())

    if name == "iris.reload":
        data_path = arguments.get("data_path", "")
        pipeline = _load_pipeline(data_path)
        if pipeline is None:
            return rpc_error(_id, -32000, f"Cannot load data from {data_path or os.environ.get('DATA_DIR', '/app/data')}")
        return rpc_result(_id, {
            "reloaded": True,
            "episode_count": pipeline["episode_count"],
            "drift_count": pipeline["drift_count"],
            "mg_node_count": pipeline["mg"].node_count,
        })

    return rpc_error(_id, -32601, f"Unknown tool: {name}")

def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            _id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})
            if method == "initialize":
                resp = rpc_result(_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sigma-overwatch-mcp", "version": "0.2.0"},
                })
            elif method == "tools/list":
                resp = handle_tools_list(_id)
            elif method == "tools/call":
                resp = handle_tools_call(_id, params)
            else:
                resp = rpc_error(_id, -32601, f"Unknown method: {method}")
        except Exception as e:
            resp = rpc_error(None, -32001, f"Server error: {e}")
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
