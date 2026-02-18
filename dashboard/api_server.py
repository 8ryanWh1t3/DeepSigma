"""DeepSigma Dashboard API Server

Serves real episode + drift data from the DeepSigma sample corpus and runs
the full coherence_ops governance pipeline, exposing the results as JSON for
the React dashboard at http://localhost:3000.

Usage
-----
    pip install fastapi uvicorn
    python dashboard/api_server.py

Endpoints
---------
    GET  /api/health      — liveness + data counts
    GET  /api/episodes    — real DecisionEpisodes in dashboard format
    GET  /api/drifts      — real DriftEvents in dashboard format
    GET  /api/agents      — per-agent metric aggregates
    GET  /api/coherence   — coherence score report (DLR/RS/DS/MG pipeline)
    POST /api/iris        — IRIS query (body: {query_type, text, episode_id})
"""

import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# ── Make coherence_ops importable ────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402

from coherence_ops import (  # noqa: E402
    DLRBuilder,
    DriftSignalCollector,
    IRISEngine,
    IRISQuery,
    MemoryGraph,
    QueryType,
    ReflectionSession,
    CoherenceScorer,
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="DeepSigma Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data paths ────────────────────────────────────────────────────────────────
_EP_DIRS = [
    REPO_ROOT / "examples" / "episodes",
    REPO_ROOT / "coherence_ops" / "examples",
]
_DRIFT_PATHS = [
    REPO_ROOT / "coherence_ops" / "examples" / "sample_drift.json",
    REPO_ROOT / "examples" / "drift",
]


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_episodes() -> List[Dict[str, Any]]:
    episodes: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for ep_dir in _EP_DIRS:
        if not ep_dir.is_dir():
            continue
        for fp in sorted(ep_dir.glob("*.json")):
            if fp.name.startswith("sample_drift"):
                continue
            try:
                data = json.loads(fp.read_text())
            except Exception:
                continue
            # Handle both single episode and list
            items = data if isinstance(data, list) else [data]
            for ep in items:
                if isinstance(ep, dict) and ep.get("episodeId") not in seen:
                    seen.add(ep.get("episodeId", ""))
                    episodes.append(ep)

    return episodes


def _load_drifts() -> List[Dict[str, Any]]:
    drifts: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for path in _DRIFT_PATHS:
        if path.is_file():
            try:
                data = json.loads(path.read_text())
                items = data if isinstance(data, list) else [data]
                for d in items:
                    if isinstance(d, dict) and d.get("driftId") not in seen:
                        seen.add(d.get("driftId", ""))
                        drifts.append(d)
            except Exception:
                pass
        elif path.is_dir():
            for fp in sorted(path.glob("*.json")):
                try:
                    data = json.loads(fp.read_text())
                    items = data if isinstance(data, list) else [data]
                    for d in items:
                        if isinstance(d, dict) and d.get("driftId") not in seen:
                            seen.add(d.get("driftId", ""))
                            drifts.append(d)
                except Exception:
                    pass

    return drifts


# ── Transformers (DeepSigma schema → Dashboard schema) ───────────────────────

_OUTCOME_TO_STATUS = {
    "success": "success",
    "partial": "degraded",
    "fail": "failed",
    "abstain": "degraded",
    "bypassed": "failed",
}

_DS_SEVERITY_MAP = {
    "green": "low",
    "yellow": "medium",
    "red": "high",
}

_DS_TYPE_ALLOWED = {"time", "freshness", "fallback", "bypass", "verify", "outcome"}


def _ts_ms(iso: str) -> int:
    """Parse ISO 8601 string → Unix milliseconds, 0 on failure."""
    if not iso:
        return 0
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def _episode_to_dashboard(ep: Dict[str, Any], drift_lookup: Dict[str, List]) -> Dict[str, Any]:
    telem = ep.get("telemetry", {})
    outcome = ep.get("outcome", {})
    context = ep.get("context", {})
    actions = ep.get("actions", [])
    verification = ep.get("verification", {})

    start_iso = (
        ep.get("startedAt")
        or ep.get("sealedAt")
        or ep.get("seal", {}).get("sealedAt", "")
    )
    ts_ms = _ts_ms(start_iso)

    ttl_breaches = context.get("ttlBreachesCount", 0)
    freshness = max(0, 100 - ttl_breaches * 20)

    ttl_ms = context.get("ttlMs", 1000) or 1000
    max_age_ms = context.get("maxFeatureAgeMs", ttl_ms)
    data_age = round((max_age_ms / ttl_ms) * 100)

    deadline = telem.get("p95Ms") or telem.get("endToEndMs") or 100
    duration = telem.get("endToEndMs") or deadline

    # AL6 score: perfect = 100, degrades as duration overshoots deadline
    overshoot = max(0, duration - deadline)
    al6_score = max(0.0, round(100.0 - (overshoot / max(deadline, 1)) * 100, 1))

    ep_id = ep.get("episodeId", "")

    return {
        "episodeId": ep_id,
        "agentName": ep.get("actor", {}).get("id", "unknown"),
        "timestamp": ts_ms,
        "deadline": deadline,
        "actualDuration": duration,
        "status": _OUTCOME_TO_STATUS.get(outcome.get("code", ""), "failed"),
        "freshness": freshness,
        "dataAge": data_age,
        "distance": telem.get("hopCount", 1),
        "variability": telem.get("jitterMs", 0),
        "drag": (
            telem.get("stageMs", {}).get("plan", 0)
            + telem.get("stageMs", {}).get("verify", 0)
        ),
        "decision": ep.get("plan", {}).get("summary") or ep.get("decisionType", ""),
        "verification": verification.get("result", "na"),
        "outcome": outcome.get("reason") or outcome.get("code", ""),
        "actionContract": actions[0].get("actionType", "") if actions else "",
        "al6Score": al6_score,
    }


def _drift_to_dashboard(dr: Dict[str, Any]) -> Dict[str, Any]:
    drift_type = dr.get("driftType", "outcome")
    if drift_type not in _DS_TYPE_ALLOWED:
        drift_type = "outcome"

    return {
        "driftId": dr.get("driftId", ""),
        "episodeId": dr.get("episodeId", ""),
        "type": drift_type,
        "severity": _DS_SEVERITY_MAP.get(dr.get("severity", "green"), "low"),
        "timestamp": _ts_ms(dr.get("detectedAt", "")),
        "patchHint": dr.get("notes") or dr.get("recommendedPatchType", ""),
        "delta": dr.get("delta", 0),
        "threshold": dr.get("threshold", 0),
    }


def _build_agent_metrics(
    episodes: List[Dict[str, Any]], drifts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    agents: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "success": 0,
            "total": 0,
            "latencies": [],
            "freshnesses": [],
            "driftCount": 0,
            "timeouts": 0,
            "degraded": 0,
            "lastSeen": 0,
        }
    )

    ep_agent_map: Dict[str, str] = {}
    for ep in episodes:
        agent = ep.get("actor", {}).get("id", "unknown")
        ep_id = ep.get("episodeId", "")
        ep_agent_map[ep_id] = agent

        a = agents[agent]
        a["total"] += 1

        outcome = ep.get("outcome", {}).get("code", "")
        if outcome == "success":
            a["success"] += 1
        elif outcome in ("abstain", "partial"):
            a["degraded"] += 1

        telem = ep.get("telemetry", {})
        if telem.get("endToEndMs"):
            a["latencies"].append(telem["endToEndMs"])

        context = ep.get("context", {})
        ttl_breaches = context.get("ttlBreachesCount", 0)
        a["freshnesses"].append(max(0, 100 - ttl_breaches * 20))

        ts_ms = _ts_ms(ep.get("startedAt", ""))
        a["lastSeen"] = max(a["lastSeen"], ts_ms)

    for dr in drifts:
        ep_id = dr.get("episodeId", "")
        agent = ep_agent_map.get(ep_id, "unknown")
        agents[agent]["driftCount"] += 1

    results = []
    for name, a in agents.items():
        lats = sorted(a["latencies"])
        n = len(lats)
        total = a["total"]
        results.append(
            {
                "agentName": name,
                "successRate": round(a["success"] / total * 100, 1) if total else 0.0,
                "avgLatency": round(sum(lats) / n) if n else 0,
                "p95Latency": lats[max(0, int(n * 0.95) - 1)] if n else 0,
                "p99Latency": lats[max(0, int(n * 0.99) - 1)] if n else 0,
                "timeoutRate": round(a["timeouts"] / total * 100, 1) if total else 0.0,
                "degradedRate": round(a["degraded"] / total * 100, 1) if total else 0.0,
                "averageFreshness": (
                    round(sum(a["freshnesses"]) / len(a["freshnesses"]), 1)
                    if a["freshnesses"]
                    else 100.0
                ),
                "episodeCount": total,
                "driftCount": a["driftCount"],
            }
        )

    return results


# ── Pipeline helper ───────────────────────────────────────────────────────────

def _build_pipeline(episodes: List[Dict[str, Any]], drifts: List[Dict[str, Any]]):
    """Build the full DLR/RS/DS/MG coherence pipeline from loaded data."""
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    rs = ReflectionSession("api-rs-001")
    rs.ingest(episodes)

    ds = DriftSignalCollector()
    ds.ingest(drifts)

    mg = MemoryGraph()
    for ep in episodes:
        mg.add_episode(ep)

    return dlr, rs, ds, mg


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    episodes = _load_episodes()
    drifts = _load_drifts()
    return {
        "status": "ok",
        "episode_count": len(episodes),
        "drift_count": len(drifts),
        "repo_root": str(REPO_ROOT),
    }


@app.get("/api/episodes")
def get_episodes():
    episodes = _load_episodes()
    drifts = _load_drifts()
    drift_lookup: Dict[str, List] = defaultdict(list)
    for dr in drifts:
        drift_lookup[dr.get("episodeId", "")].append(dr)
    return [_episode_to_dashboard(ep, drift_lookup) for ep in episodes]


@app.get("/api/drifts")
def get_drifts():
    return [_drift_to_dashboard(dr) for dr in _load_drifts()]


@app.get("/api/agents")
def get_agents():
    return _build_agent_metrics(_load_episodes(), _load_drifts())


@app.get("/api/coherence")
def get_coherence():
    """Run the full coherence_ops pipeline and return the scored report."""
    episodes = _load_episodes()
    drifts = _load_drifts()
    if not episodes:
        raise HTTPException(status_code=404, detail="No episodes found")

    dlr, rs, ds, mg = _build_pipeline(episodes, drifts)

    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    from dataclasses import asdict
    return asdict(report)


@app.post("/api/iris")
def query_iris(body: Dict[str, Any]):
    """
    Run an IRIS query against the loaded episode corpus.

    Body (JSON):
        query_type  : "WHY" | "WHAT_CHANGED" | "WHAT_DRIFTED" | "RECALL" | "STATUS"
        text        : free-text question (optional)
        episode_id  : target episode ID (optional)
        decision_type: filter by decision type (optional)
    """
    episodes = _load_episodes()
    drifts = _load_drifts()
    if not episodes:
        raise HTTPException(status_code=404, detail="No episodes found")

    dlr, _rs, _ds, mg = _build_pipeline(episodes, drifts)

    # IRISEngine takes memory_graph and dlr_entries (list of dicts)
    engine = IRISEngine(memory_graph=mg, dlr_entries=dlr.to_dict_list())
    query = IRISQuery(
        query_type=body.get("query_type", QueryType.STATUS),
        text=body.get("text", ""),
        episode_id=body.get("episode_id", ""),
        decision_type=body.get("decision_type", ""),
    )
    response = engine.resolve(query)
    return response.to_dict()


@app.get("/api/mg")
def get_mg():
    """Return Memory Graph nodes + edges as JSON."""
    episodes = _load_episodes()
    drifts = _load_drifts()
    if not episodes:
        return {"nodes": [], "edges": []}
    _, _, _, mg = _build_pipeline(episodes, drifts)
    return json.loads(mg.to_json())


@app.get("/api/sse")
async def sse_stream():
    """SSE stream: multiplexes episodes, drifts, agents, mg events."""
    async def event_generator():
        last_hash = ""
        while True:
            try:
                episodes = _load_episodes()
                drifts = _load_drifts()
                current_hash = f"{len(episodes)}:{len(drifts)}"
                if current_hash != last_hash:
                    drift_lookup: Dict[str, List] = defaultdict(list)
                    for dr in drifts:
                        drift_lookup[dr.get("episodeId", "")].append(dr)
                    ep_data = [_episode_to_dashboard(ep, drift_lookup) for ep in episodes]
                    drift_data = [_drift_to_dashboard(dr) for dr in drifts]
                    agent_data = _build_agent_metrics(episodes, drifts)
                    yield f"event: episodes\ndata: {json.dumps(ep_data)}\n\n"
                    yield f"event: drifts\ndata: {json.dumps(drift_data)}\n\n"
                    yield f"event: agents\ndata: {json.dumps(agent_data)}\n\n"
                    if episodes:
                        _, _, _, mg = _build_pipeline(episodes, drifts)
                        yield f"event: mg\ndata: {mg.to_json()}\n\n"
                    last_hash = current_hash
                yield ": keepalive\n\n"
            except Exception:
                yield ": error\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Repo root: {REPO_ROOT}")
    print(f"Episodes dir: {REPO_ROOT / 'examples' / 'episodes'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
