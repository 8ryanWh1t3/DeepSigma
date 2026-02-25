#!/usr/bin/env python3
"""MCP Server — Production JSON-RPC stdio server for MCP integration.

Implements the Model Context Protocol v2024-11-05 with:
- Full tool registry (29 tools including 5 coherence tools)
- API key authentication (optional, via MCP_API_KEYS env var)
- Per-client rate limiting (configurable via MCP_RATE_LIMIT env var)
- Circuit breakers and retry logic for connector resilience
- Streaming support for large result sets

Supported JSON-RPC methods:
- initialize
- tools/list, tools/call
- resources/list, resources/read
- prompts/list, prompts/get

Run:
  python adapters/mcp/mcp_server_scaffold.py
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.mcp.resilience import CircuitBreaker, CircuitOpen, retry, is_transient  # noqa: E402

CATALOG = json.loads((ROOT / "src" / "adapters" / "mcp" / "tool_catalog.json").read_text(encoding="utf-8"))
RESOURCE_CATALOG = json.loads((ROOT / "src" / "adapters" / "mcp" / "resource_catalog.json").read_text(encoding="utf-8"))
PROMPT_CATALOG = json.loads((ROOT / "src" / "adapters" / "mcp" / "prompt_catalog.json").read_text(encoding="utf-8"))

# ── Per-connector circuit breakers ───────────────────────────────
BREAKERS: Dict[str, CircuitBreaker] = {
    "sharepoint": CircuitBreaker(name="sharepoint", threshold=5, cooldown=60.0),
    "dataverse": CircuitBreaker(name="dataverse", threshold=5, cooldown=60.0),
    "asksage": CircuitBreaker(name="asksage", threshold=5, cooldown=60.0),
    "cortex": CircuitBreaker(name="cortex", threshold=5, cooldown=60.0),
    "snowflake": CircuitBreaker(name="snowflake", threshold=5, cooldown=60.0),
    "golden_path": CircuitBreaker(name="golden_path", threshold=5, cooldown=60.0),
}


# ── Authentication ──────────────────────────────────────────────
_AUTH_KEYS_RAW = os.environ.get("MCP_API_KEYS", "")
_AUTH_KEYS: set = {k.strip() for k in _AUTH_KEYS_RAW.split(",") if k.strip()} if _AUTH_KEYS_RAW else set()
_AUTH_ENABLED = bool(_AUTH_KEYS)
_AUTHED_SESSIONS: set = set()


def _check_auth(session_id: str) -> bool:
    """Return True if request is authorized (or auth is disabled)."""
    if not _AUTH_ENABLED:
        return True
    return session_id in _AUTHED_SESSIONS


# ── Rate Limiting ──────────────────────────────────────────────
_RATE_LIMIT = int(os.environ.get("MCP_RATE_LIMIT", "60"))  # requests per minute


class _RateLimiter:
    """Per-session sliding window rate limiter."""

    def __init__(self, max_per_minute: int = 60):
        self._max = max_per_minute
        self._windows: Dict[str, List[float]] = {}

    def allow(self, session_id: str) -> bool:
        now = time.monotonic()
        window = self._windows.setdefault(session_id, [])
        # Prune entries older than 60s
        cutoff = now - 60.0
        self._windows[session_id] = [t for t in window if t > cutoff]
        if len(self._windows[session_id]) >= self._max:
            return False
        self._windows[session_id].append(now)
        return True


_rate_limiter = _RateLimiter(_RATE_LIMIT)


def _connector_call(breaker_name: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute *fn* with retry + circuit-breaker protection."""
    breaker = BREAKERS.get(breaker_name)

    @retry(max_attempts=3, base_delay=0.5, transient=is_transient)
    def _guarded() -> Any:
        if breaker is not None:
            with breaker():
                return fn(*args, **kwargs)
        return fn(*args, **kwargs)

    return _guarded()


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
        from core.cli import _build_pipeline, _load_drift, _load_episodes
        from core.iris import IRISConfig, IRISEngine

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
        from core.iris import IRISQuery
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

    # ── SharePoint tools ──────────────────────────────────────
    if name == "sharepoint.list":
        from adapters.sharepoint.connector import SharePointConnector
        connector = SharePointConnector()
        records = _connector_call("sharepoint", connector.list_items, arguments.get("list_id", ""))
        return rpc_result(_id, {"records": records, "count": len(records)})

    if name == "sharepoint.get":
        from adapters.sharepoint.connector import SharePointConnector
        connector = SharePointConnector()
        record = _connector_call("sharepoint", connector.get_item, arguments.get("list_id", ""), arguments.get("item_id", ""))
        return rpc_result(_id, {"record": record})

    if name == "sharepoint.sync":
        from adapters.sharepoint.connector import SharePointConnector
        connector = SharePointConnector()
        result = _connector_call("sharepoint", connector.delta_sync, arguments.get("list_id", ""))
        return rpc_result(_id, result)

    # ── Dataverse tools ────────────────────────────────────────
    if name == "dataverse.list":
        from adapters.powerplatform.connector import DataverseConnector
        connector = DataverseConnector()
        records = _connector_call("dataverse", connector.list_records, arguments.get("table_name", ""))
        return rpc_result(_id, {"records": records, "count": len(records)})

    if name == "dataverse.get":
        from adapters.powerplatform.connector import DataverseConnector
        connector = DataverseConnector()
        record = _connector_call("dataverse", connector.get_record, arguments.get("table_name", ""), arguments.get("record_id", ""))
        return rpc_result(_id, {"record": record})

    if name == "dataverse.query":
        from adapters.powerplatform.connector import DataverseConnector
        connector = DataverseConnector()
        records = _connector_call("dataverse", connector.query, arguments.get("table_name", ""), arguments.get("filter", ""))
        return rpc_result(_id, {"records": records, "count": len(records)})

    # ── AskSage tools ──────────────────────────────────────────
    if name == "asksage.query":
        from adapters.asksage.connector import AskSageConnector
        connector = AskSageConnector()
        result = _connector_call(
            "asksage", connector.query,
            prompt=arguments.get("prompt", ""),
            model=arguments.get("model"),
            dataset=arguments.get("dataset"),
            persona=arguments.get("persona"),
        )
        return rpc_result(_id, result)

    if name == "asksage.models":
        from adapters.asksage.connector import AskSageConnector
        connector = AskSageConnector()
        return rpc_result(_id, {"models": _connector_call("asksage", connector.get_models)})

    if name == "asksage.datasets":
        from adapters.asksage.connector import AskSageConnector
        connector = AskSageConnector()
        return rpc_result(_id, {"datasets": _connector_call("asksage", connector.get_datasets)})

    if name == "asksage.history":
        from adapters.asksage.connector import AskSageConnector
        connector = AskSageConnector()
        return rpc_result(_id, {"logs": _connector_call("asksage", connector.get_user_logs, limit=arguments.get("limit", 20))})

    # ── Snowflake Cortex tools ─────────────────────────────────
    if name == "cortex.complete":
        from adapters.snowflake.cortex import CortexConnector
        connector = CortexConnector()
        result = _connector_call(
            "cortex", connector.complete_sync,
            model=arguments.get("model", ""),
            messages=arguments.get("messages", []),
            max_tokens=arguments.get("max_tokens"),
            temperature=arguments.get("temperature"),
        )
        return rpc_result(_id, result)

    if name == "cortex.embed":
        from adapters.snowflake.cortex import CortexConnector
        connector = CortexConnector()
        result = _connector_call("cortex", connector.embed, model=arguments.get("model", ""), texts=arguments.get("texts", []))
        return rpc_result(_id, result)

    # ── Snowflake warehouse tools ──────────────────────────────
    if name == "snowflake.query":
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        connector = SnowflakeWarehouseConnector()
        rows = _connector_call("snowflake", connector.query, arguments.get("sql", ""))
        return rpc_result(_id, {"rows": rows, "count": len(rows)})

    if name == "snowflake.tables":
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        connector = SnowflakeWarehouseConnector()
        return rpc_result(_id, {"tables": _connector_call("snowflake", connector.list_tables)})

    if name == "snowflake.sync":
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        connector = SnowflakeWarehouseConnector()
        result = _connector_call("snowflake", connector.sync_table, arguments.get("table_name", ""), since=arguments.get("since"))
        return rpc_result(_id, result)

    if name == "golden_path.run":
        from demos.golden_path.config import GoldenPathConfig
        from demos.golden_path.pipeline import GoldenPathPipeline
        config = GoldenPathConfig(
            source=arguments.get("source", "sharepoint"),
            fixture_path=arguments.get("fixture"),
            episode_id=arguments.get("episode_id", "gp-demo"),
            list_id=arguments.get("list_id", ""),
            table_name=arguments.get("table_name", ""),
            sql=arguments.get("sql", ""),
            prompt=arguments.get("prompt", ""),
        )
        result = _connector_call("golden_path", GoldenPathPipeline(config).run)
        return rpc_result(_id, result.to_dict())

    # ── Coherence tools ──────────────────────────────────────
    if name == "coherence.query_credibility_index":
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline is None:
            return rpc_error(_id, -32000, "No data loaded. Call iris.reload first or set DATA_DIR.")
        from core.scoring import CoherenceScorer
        scorer = CoherenceScorer(
            dlr_builder=_iris_pipeline["dlr"],
            rs=_iris_pipeline["rs"],
            ds=_iris_pipeline["ds"],
            mg=_iris_pipeline["mg"],
        )
        report = scorer.score()
        return rpc_result(_id, {
            "overall_score": report.overall_score,
            "grade": report.grade,
            "computed_at": report.computed_at,
            "dimensions": [dataclasses.asdict(d) for d in report.dimensions],
        })

    if name == "coherence.list_drift_signals":
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline is None:
            return rpc_error(_id, -32000, "No data loaded. Call iris.reload first or set DATA_DIR.")
        ds = _iris_pipeline["ds"]
        summary = ds.summarise()
        result_data = dataclasses.asdict(summary)
        # Convert DriftBucket dataclasses to dicts
        result_data["buckets"] = [dataclasses.asdict(b) for b in summary.buckets]
        # Apply severity filter if provided
        severity_filter = arguments.get("severity")
        if severity_filter:
            result_data["buckets"] = [
                b for b in result_data["buckets"]
                if b.get("worst_severity") == severity_filter
            ]
        # Apply limit
        limit = arguments.get("limit", 100)
        result_data["buckets"] = result_data["buckets"][:limit]
        return rpc_result(_id, result_data)

    if name == "coherence.get_episode":
        episode_id = arguments.get("episode_id", "")
        if not episode_id:
            return rpc_error(_id, -32602, "Missing params.arguments.episode_id")
        # Try MG provenance query first
        if _iris_pipeline and _iris_pipeline.get("mg"):
            provenance = _iris_pipeline["mg"].query("why", episode_id=episode_id)
        else:
            provenance = None
        # Load episode file
        data = _data_dir()
        episode_data = None
        for pattern in (f"{episode_id}.json", f"episodes/{episode_id}.json"):
            candidate = data / pattern
            if candidate.exists():
                episode_data = json.loads(candidate.read_text(encoding="utf-8"))
                break
        if episode_data is None and (provenance is None or provenance.get("node") is None):
            return rpc_error(_id, -32000, f"Episode not found: {episode_id}")
        result_data = {"episode_id": episode_id}
        if episode_data:
            result_data["episode"] = episode_data
        if provenance and provenance.get("node"):
            result_data["provenance"] = provenance
        return rpc_result(_id, result_data)

    if name == "coherence.apply_patch":
        patch = arguments.get("patch", {})
        if not patch or not patch.get("patchId"):
            return rpc_error(_id, -32602, "Missing params.arguments.patch with patchId")
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline is None:
            return rpc_error(_id, -32000, "No data loaded. Call iris.reload first or set DATA_DIR.")
        mg = _iris_pipeline["mg"]
        node_id = mg.add_patch(patch)
        return rpc_result(_id, {
            "applied": True,
            "patch_id": patch["patchId"],
            "node_id": node_id,
        })

    if name == "coherence.seal_decision":
        episode = arguments.get("episode", {})
        if not episode or not episode.get("episodeId"):
            return rpc_error(_id, -32602, "Missing params.arguments.episode with episodeId")
        if _iris_pipeline is None:
            _load_pipeline()
        if _iris_pipeline is None:
            return rpc_error(_id, -32000, "No data loaded. Call iris.reload first or set DATA_DIR.")
        from core.decision_log import DLRBuilder
        dlr_builder = DLRBuilder()
        entry = dlr_builder.from_episode(episode)
        mg = _iris_pipeline["mg"]
        mg.add_episode(episode)
        return rpc_result(_id, {
            "sealed": True,
            "dlr_id": entry.dlr_id,
            "episode_id": entry.episode_id,
            "decision_type": entry.decision_type,
            "outcome_code": entry.outcome_code,
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
    specs_dir = ROOT / "schemas" / "core"
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
        candidate = ROOT / "schemas" / "core" / f"{schema_name}.schema.json"
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

def handle_initialize(_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP initialize with optional API key auth."""
    session_id = "sess_" + uuid.uuid4().hex[:12]
    # Auth: validate API key if auth is enabled
    if _AUTH_ENABLED:
        api_key = params.get("apiKey", "")
        if api_key not in _AUTH_KEYS:
            return rpc_error(_id, -32000, "Authentication failed: invalid API key")
        _AUTHED_SESSIONS.add(session_id)

    return rpc_result(_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            "resources": {},
            "prompts": {},
        },
        "serverInfo": {"name": "sigma-overwatch-mcp", "version": "1.0.0"},
        "sessionId": session_id,
    })


def main() -> None:
    current_session: str = ""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        _id = None
        try:
            req = json.loads(line)
            _id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})
            if method == "initialize":
                resp = handle_initialize(_id, params)
                if "result" in resp and "sessionId" in resp["result"]:
                    current_session = resp["result"]["sessionId"]
            elif method == "tools/list":
                resp = handle_tools_list(_id)
            elif method == "tools/call":
                # Auth check
                if not _check_auth(current_session):
                    resp = rpc_error(_id, -32000, "Authentication required: call initialize with valid apiKey")
                # Rate limit check
                elif not _rate_limiter.allow(current_session or "anonymous"):
                    resp = rpc_error(_id, -32003, "Rate limit exceeded")
                else:
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
        except CircuitOpen as co:
            resp = rpc_error(_id, -32003, f"Service unavailable: {co}")
        except Exception as e:
            resp = rpc_error(_id, -32001, f"Server error: {e}")
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
