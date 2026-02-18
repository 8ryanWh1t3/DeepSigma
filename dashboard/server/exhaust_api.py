"""Exhaust Inbox API router.

FastAPI router providing endpoints for the Exhaust Inbox system:
event ingestion, episode assembly, refinement, commit, and drift queries.

Storage: file-based MVP using /app/data/ subdirectories.
Assumes uvicorn --workers 1 (single-writer).
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, HTTPException, Query
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    from .models_exhaust import (
        DecisionEpisode,
        DriftSignal,
        EpisodeEvent,
        HealthResponse,
        ItemAction,
        RefinedEpisode,
        Source,
    )

# ── Storage paths ────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
EVENTS_FILE = DATA_DIR / "events.jsonl"
EPISODES_DIR = DATA_DIR / "episodes"
REFINED_DIR = DATA_DIR / "refined"
MG_DIR = DATA_DIR / "mg"
DRIFT_DIR = DATA_DIR / "drift"
MG_FILE = MG_DIR / "memory_graph.jsonl"
DRIFT_FILE = DRIFT_DIR / "drift.jsonl"

# Single-writer lock (safe with --workers 1)
_write_lock = threading.Lock()


def _ensure_dirs() -> None:
    """Create storage directories if they don't exist."""
    for d in [DATA_DIR, EPISODES_DIR, REFINED_DIR, MG_DIR, DRIFT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    """Append a JSON line to a JSONL file with locking."""
    with _write_lock:
        _ensure_dirs()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read all lines from a JSONL file."""
    if not path.exists():
        return []
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return results


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write a single JSON file with locking."""
    with _write_lock:
        _ensure_dirs()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read a single JSON file."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ── Router ───────────────────────────────────────────────────────

if HAS_FASTAPI:
    router = APIRouter(prefix="/api/exhaust", tags=["exhaust"])

    @router.get("/health", response_model=HealthResponse)
    def exhaust_health():
        """Health check for the exhaust module."""
        _ensure_dirs()
        events = _read_jsonl(EVENTS_FILE)
        episodes = list(EPISODES_DIR.glob("*.json")) if EPISODES_DIR.exists() else []
        refined = list(REFINED_DIR.glob("*.json")) if REFINED_DIR.exists() else []
        drift = _read_jsonl(DRIFT_FILE)
        return HealthResponse(
            events_count=len(events),
            episodes_count=len(episodes),
            refined_count=len(refined),
            drift_count=len(drift),
        )

    @router.get("/schema")
    def exhaust_schema():
        """Export JSON schemas for all exhaust models."""
        return {
            "EpisodeEvent": EpisodeEvent.model_json_schema(),
            "DecisionEpisode": DecisionEpisode.model_json_schema(),
            "RefinedEpisode": RefinedEpisode.model_json_schema(),
            "DriftSignal": DriftSignal.model_json_schema(),
        }

    # ── Event ingestion ──────────────────────────────────────────

    @router.post("/events")
    def ingest_event(event: EpisodeEvent):
        """Ingest a single raw EpisodeEvent."""
        _append_jsonl(EVENTS_FILE, event.model_dump())
        return {"status": "accepted", "event_id": event.event_id, "episode_id": event.episode_id}

    # ── Episode assembly ─────────────────────────────────────────

    @router.post("/episodes/assemble")
    def assemble_episodes(
        episode_id: Optional[str] = Query(None, description="Assemble specific episode; omit for all pending"),
    ):
        """Group events into DecisionEpisodes."""
        events = _read_jsonl(EVENTS_FILE)
        # Group by episode_id
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for ev in events:
            eid = ev.get("episode_id", "")
            if episode_id and eid != episode_id:
                continue
            groups.setdefault(eid, []).append(ev)

        assembled = []
        for eid, evts in groups.items():
            ep_path = EPISODES_DIR / f"{eid}.json"
            if ep_path.exists():
                continue  # Already assembled
            sorted_evts = sorted(evts, key=lambda e: e.get("timestamp", ""))
            episode = DecisionEpisode(
                episode_id=eid,
                events=[EpisodeEvent(**e) for e in sorted_evts],
                source=Source(sorted_evts[0].get("source", "manual")),
                user_hash=sorted_evts[0].get("user_hash", "anon"),
                session_id=sorted_evts[0].get("session_id", ""),
                project=sorted_evts[0].get("project", "default"),
                team=sorted_evts[0].get("team", "default"),
                started_at=sorted_evts[0].get("timestamp", ""),
                ended_at=sorted_evts[-1].get("timestamp", ""),
            )
            _write_json(ep_path, episode.model_dump())
            assembled.append(eid)

        return {"assembled": len(assembled), "episode_ids": assembled}

    # ── Episode listing / detail ─────────────────────────────────

    @router.get("/episodes")
    def list_episodes(
        project: Optional[str] = Query(None),
        team: Optional[str] = Query(None),
        source: Optional[str] = Query(None),
        drift_only: bool = Query(False),
        low_confidence_only: bool = Query(False),
        min_score: Optional[float] = Query(None),
        max_score: Optional[float] = Query(None),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        """List episodes with filters."""
        _ensure_dirs()
        episodes = []
        for f in sorted(EPISODES_DIR.glob("*.json")):
            data = _read_json(f)
            if data:
                episodes.append(data)

        # Apply filters
        if project:
            episodes = [e for e in episodes if e.get("project") == project]
        if team:
            episodes = [e for e in episodes if e.get("team") == team]
        if source:
            episodes = [e for e in episodes if e.get("source") == source]
        if min_score is not None:
            episodes = [e for e in episodes if (e.get("coherence_score") or 0) >= min_score]
        if max_score is not None:
            episodes = [e for e in episodes if (e.get("coherence_score") or 100) <= max_score]
        if low_confidence_only:
            episodes = [e for e in episodes if (e.get("coherence_score") or 0) < 65]

        # Check for drift if drift_only
        if drift_only:
            drift_eids = set()
            for d in _read_jsonl(DRIFT_FILE):
                drift_eids.add(d.get("episode_id", ""))
            episodes = [e for e in episodes if e.get("episode_id") in drift_eids]

        total = len(episodes)
        episodes = episodes[offset:offset + limit]

        return {"total": total, "count": len(episodes), "episodes": episodes}

    @router.get("/episodes/{episode_id}")
    def get_episode_detail(episode_id: str):
        """Get full episode detail including refined data if available."""
        ep = _read_json(EPISODES_DIR / f"{episode_id}.json")
        if not ep:
            raise HTTPException(404, f"Episode {episode_id} not found")
        refined = _read_json(REFINED_DIR / f"{episode_id}.json")
        return {"episode": ep, "refined": refined}

    # ── Refinement ───────────────────────────────────────────────

    @router.post("/episodes/{episode_id}/refine")
    def refine_episode(episode_id: str):
        """Run extraction/refinement on an episode."""
        ep_data = _read_json(EPISODES_DIR / f"{episode_id}.json")
        if not ep_data:
            raise HTTPException(404, f"Episode {episode_id} not found")

        episode = DecisionEpisode(**ep_data)

        # Import refiner (lazy to avoid circular deps)
        try:
            from engine.exhaust_refiner import refine_episode as do_refine
            use_llm = os.environ.get("EXHAUST_USE_LLM", "0") == "1"
            refined = do_refine(episode, use_llm=use_llm)
        except ImportError:
            # Fallback: minimal stub refinement
            refined = RefinedEpisode(
                episode_id=episode_id,
                coherence_score=50.0,
                grade="D",
            )

        _write_json(REFINED_DIR / f"{episode_id}.json", refined.model_dump())

        # Update episode status
        ep_data["refined"] = True
        ep_data["coherence_score"] = refined.coherence_score
        ep_data["grade"] = refined.grade
        _write_json(EPISODES_DIR / f"{episode_id}.json", ep_data)

        return {"status": "refined", "episode_id": episode_id, "coherence_score": refined.coherence_score, "grade": refined.grade}

    # ── Commit ───────────────────────────────────────────────────

    @router.post("/episodes/{episode_id}/commit")
    def commit_episode(episode_id: str):
        """Accept and commit refined items to memory graph + seal episode."""
        refined_data = _read_json(REFINED_DIR / f"{episode_id}.json")
        if not refined_data:
            raise HTTPException(404, f"Refined data for {episode_id} not found")

        # Write accepted items to memory graph
        for bucket in ["truth", "reasoning", "memory"]:
            for item in refined_data.get(bucket, []):
                if item.get("status", "pending") != "rejected":
                    _append_jsonl(MG_FILE, {
                        "node_type": bucket,
                        "episode_id": episode_id,
                        **item,
                    })

        # Write drift signals
        for drift in refined_data.get("drift_signals", []):
            _append_jsonl(DRIFT_FILE, drift)

        # Mark committed
        refined_data["committed"] = True
        _write_json(REFINED_DIR / f"{episode_id}.json", refined_data)

        ep_data = _read_json(EPISODES_DIR / f"{episode_id}.json")
        if ep_data:
            ep_data["status"] = "committed"
            _write_json(EPISODES_DIR / f"{episode_id}.json", ep_data)

        return {"status": "committed", "episode_id": episode_id}

    # ── Single item action ───────────────────────────────────────

    @router.post("/episodes/{episode_id}/item")
    def item_action(episode_id: str, action: ItemAction):
        """Accept/reject/edit a single refined item."""
        refined_data = _read_json(REFINED_DIR / f"{episode_id}.json")
        if not refined_data:
            raise HTTPException(404, f"Refined data for {episode_id} not found")

        bucket_items = refined_data.get(action.bucket, [])
        found = False
        for item in bucket_items:
            if item.get("item_id") == action.item_id:
                if action.action == "accept":
                    item["status"] = "accepted"
                elif action.action == "reject":
                    item["status"] = "rejected"
                elif action.action == "edit" and action.edited_data:
                    item.update(action.edited_data)
                    item["status"] = "edited"
                found = True
                break

        if not found:
            raise HTTPException(404, f"Item {action.item_id} not found in {action.bucket}")

        _write_json(REFINED_DIR / f"{episode_id}.json", refined_data)
        return {"status": action.action, "item_id": action.item_id}

    # ── Drift listing ────────────────────────────────────────────

    @router.get("/drift")
    def list_drift(
        severity: Optional[str] = Query(None),
        drift_type: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ):
        """List drift signals."""
        signals = _read_jsonl(DRIFT_FILE)
        if severity:
            signals = [s for s in signals if s.get("severity") == severity]
        if drift_type:
            signals = [s for s in signals if s.get("drift_type") == drift_type]
        return {"count": len(signals[:limit]), "drift_signals": signals[:limit]}
