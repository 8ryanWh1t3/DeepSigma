#!/usr/bin/env python3
"""MCP Server Scaffold (dependency-free)

Minimal JSON-RPC stdio server for MCP integration.

Supported JSON-RPC methods:
- initialize
- tools/list, tools/call
- resources/list, resources/read
- prompts/list, prompts/get

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
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CATALOG = json.loads((ROOT / "adapters" / "mcp" / "tool_catalog.json").read_text(encoding="utf-8"))
RESOURCE_CATALOG = json.loads((ROOT / "adapters" / "mcp" / "resource_catalog.json").read_text(encoding="utf-8"))
PROMPT_CATALOG = json.loads((ROOT / "adapters" / "mcp" / "prompt_catalog.json").read_text(encoding="utf-8"))

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

def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/app/data"))

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

SESSIONS: Dict[str, Dict[str, Any]] = {}

def rpc_result(_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": _id, "result": result}

def rpc_error(_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}}

# ── Tools ───────────────────────────────────────────────────────

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

# ── Resources ───────────────────────────────────────────────────

def handle_resources_list(_id: Any) -> Dict[str, Any]:
    """Return available resources by scanning DATA_DIR + schemas."""
    resources: List[Dict[str, Any]] = []
    data = _data_dir()

    # Episodes
    for f in sorted(data.glob("*.json")):
        if f.name.startswith("ep") or "episode" in f.name.lower():
            ep_id = f.stem
            resources.append({
                "uri": f"episode://{ep_id}",
                "name": f"Episode {ep_id}",
                "mimeType": "application/json",
            })

    # Drift events
    for f in sorted(data.glob("*.drift.json")):
        drift_id = f.stem.replace(".drift", "")
        resources.append({
            "uri": f"drift://{drift_id}",
            "name": f"Drift {drift_id}",
            "mimeType": "application/json",
        })

    # Schemas
    specs_dir = ROOT / "specs"
    if specs_dir.exists():
        for f in sorted(specs_dir.glob("*.schema.json")):
            schema_name = f.stem.replace(".schema", "")
            resources.append({
                "uri": f"schema://{schema_name}",
                "name": f"{schema_name} schema",
                "mimeType": "application/json",
            })

    # Coherence stats (always available)
    resources.append({
        "uri": "stats://coherence",
        "name": "Coherence Stats",
        "mimeType": "application/json",
    })

    return rpc_result(_id, {"resources": resources})


def handle_resources_read(_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Read a single resource by URI."""
    uri = params.get("uri", "")
    if not uri:
        return rpc_error(_id, -32602, "Missing params.uri")

    if uri.startswith("episode://"):
        ep_id = uri.removeprefix("episode://")
        data = _data_dir()
        for pattern in (f"{ep_id}.json", f"episodes/{ep_id}.json"):
            candidate = data / pattern
            if candidate.exists():
                content = json.loads(candidate.read_text(encoding="utf-8"))
                return rpc_result(_id, {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content)}],
                })
        return rpc_error(_id, -32000, f"Episode not found: {ep_id}")

    if uri.startswith("drift://"):
        drift_id = uri.removeprefix("drift://")
        candidate = _data_dir() / f"{drift_id}.drift.json"
        if candidate.exists():
            content = json.loads(candidate.read_text(encoding="utf-8"))
            return rpc_result(_id, {
                "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content)}],
            })
        return rpc_error(_id, -32000, f"Drift event not found: {drift_id}")

    if uri.startswith("schema://"):
        schema_name = uri.removeprefix("schema://")
        candidate = ROOT / "specs" / f"{schema_name}.schema.json"
        if candidate.exists():
            content = json.loads(candidate.read_text(encoding="utf-8"))
            return rpc_result(_id, {
                "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content)}],
            })
        return rpc_error(_id, -32000, f"Schema not found: {schema_name}")

    if uri == "stats://coherence":
        global _iris_pipeline
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline and _iris_pipeline.get("mg"):
            stats = _iris_pipeline["mg"].query("stats")
        else:
            stats = {"total_nodes": 0, "total_edges": 0, "nodes_by_kind": {}, "edges_by_kind": {}}
        return rpc_result(_id, {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(stats)}],
        })

    return rpc_error(_id, -32000, f"Unknown resource URI: {uri}")

# ── Prompts ─────────────────────────────────────────────────────

def handle_prompts_list(_id: Any) -> Dict[str, Any]:
    """Return available prompts from the catalog."""
    return rpc_result(_id, {"prompts": PROMPT_CATALOG.get("prompts", [])})


def handle_prompts_get(_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a prompt with arguments interpolated into messages."""
    name = params.get("name", "")
    arguments = params.get("arguments", {})

    if name == "assemble_context":
        decision_type = arguments.get("decision_type", "unknown")
        text = (
            f"Assemble the operator context for decision type '{decision_type}'.\n\n"
            f"Include:\n"
            f"1. The DTE constraints (deadline, stage budgets, freshness TTLs, limits)\n"
            f"2. The applicable policy pack rules\n"
            f"3. Recent episodes of this type with outcomes and coherence scores\n"
            f"4. Any active drift signals related to this decision type\n\n"
            f"Present the context in a structured format suitable for decision-making."
        )
        return rpc_result(_id, {
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        })

    if name == "trace_decision":
        episode_id = arguments.get("episode_id", "unknown")
        text = (
            f"Trace the full decision chain for episode '{episode_id}'.\n\n"
            f"For each step, report:\n"
            f"1. Actions taken (type, blast radius tier, authorization)\n"
            f"2. Verification results (method, pass/fail, duration)\n"
            f"3. Degrade path (was the degrade ladder invoked? which step?)\n"
            f"4. Drift signals detected (type, severity, recommended patch)\n"
            f"5. Final outcome and coherence score\n\n"
            f"Highlight any anomalies or areas of concern."
        )
        return rpc_result(_id, {
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        })

    if name == "check_contradictions":
        episode_id = arguments.get("episode_id", "unknown")
        text = (
            f"Check episode '{episode_id}' for drift contradictions.\n\n"
            f"Compare the truth claims extracted from this episode against the memory graph canon.\n"
            f"For each contradiction found, report:\n"
            f"1. Entity and property in conflict\n"
            f"2. Expected value (from canon) vs actual value (from episode)\n"
            f"3. Severity assessment\n"
            f"4. Recommended patch action\n\n"
            f"If no contradictions are found, confirm the episode is consistent with the canon."
        )
        return rpc_result(_id, {
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        })

    return rpc_error(_id, -32000, f"Unknown prompt: {name}")

# ── Main Loop ───────────────────────────────────────────────────

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
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "serverInfo": {"name": "sigma-overwatch-mcp", "version": "0.3.0"},
                })
            elif method == "tools/list":
                resp = handle_tools_list(_id)
            elif method == "tools/call":
                resp = handle_tools_call(_id, params)
            elif method == "resources/list":
                resp = handle_resources_list(_id)
            elif method == "resources/read":
                resp = handle_resources_read(_id, params)
            elif method == "prompts/list":
                resp = handle_prompts_list(_id)
            elif method == "prompts/get":
                resp = handle_prompts_get(_id, params)
            else:
                resp = rpc_error(_id, -32601, f"Unknown method: {method}")
        except Exception as e:
            resp = rpc_error(None, -32001, f"Server error: {e}")
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
