"""
adapters/azure_openai_exhaust.py – Azure / OpenAI log ingestion adapter
========================================================================
Batch / near-real-time ingestion of OpenAI or Azure OpenAI chat logs
into the Exhaust Inbox system. Reads JSONL log files, normalises them
to EpisodeEvent payloads, groups by user_hash + conversation_id + time
window (30 min default), and POSTs to the ingestion endpoint.

Usage (CLI):
    python -m adapters.azure_openai_exhaust \
        --input /path/to/openai_logs.jsonl \
        --endpoint http://localhost:8000/api/exhaust/events

Usage (library):
    from adapters.azure_openai_exhaust import ingest_openai_logs
    ingest_openai_logs("logs.jsonl", endpoint="http://localhost:8000/api/exhaust/events")
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_ENDPOINT = "http://localhost:8000/api/exhaust/events"
DEFAULT_WINDOW_MINUTES = 30
SOURCE = "azure_openai"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _event_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(raw: Any) -> datetime:
    """Parse a timestamp from various formats."""
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Normalise a single OpenAI / Azure log entry → list of EpisodeEvents
# ---------------------------------------------------------------------------

def _normalise_entry(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a single OpenAI API log entry into EpisodeEvent dicts.

    Supports the common shapes:
      - {"messages": [...], "model": ...}  (chat completion request)
      - {"choices": [...]}                 (chat completion response)
      - Azure logs with "request" / "response" keys
    """
    events: List[Dict[str, Any]] = []

    ts_raw = entry.get("created") or entry.get("timestamp") or entry.get("created_at") or _utcnow()
    ts = _parse_ts(ts_raw)
    ts_iso = ts.isoformat()

    user_raw = (
        entry.get("user")
        or entry.get("user_id")
        or entry.get("metadata", {}).get("user_id")
        or ""
    )
    user_hash = _hash(str(user_raw)) if user_raw else "anon"

    conv_id = (
        entry.get("conversation_id")
        or entry.get("session_id")
        or entry.get("id")
        or ""
    )

    model = entry.get("model") or entry.get("engine") or "unknown"
    project = entry.get("project") or entry.get("metadata", {}).get("project") or "default"
    team = entry.get("team") or entry.get("metadata", {}).get("team") or ""

    base = {
        "session_id": str(conv_id),
        "user_hash": user_hash,
        "source": SOURCE,
        "project": project,
        "team": team,
    }

    # --- request messages ---
    messages = entry.get("messages") or (entry.get("request", {}) or {}).get("messages") or []
    for i, msg in enumerate(messages):
        role = msg.get("role", "user")
        content_str = msg.get("content") or ""
        etype = "prompt" if role in ("user", "system") else "response"
        events.append({
            **base,
            "event_id": _event_id(str(conv_id), ts_iso, str(i)),
            "episode_id": "",
            "event_type": etype,
            "timestamp": ts_iso,
            "payload": content_str[:4000],
            "meta": {"role": role, "model": model},
        })

    # --- response choices ---
    choices = entry.get("choices") or (entry.get("response", {}) or {}).get("choices") or []
    for i, choice in enumerate(choices):
        msg = choice.get("message") or choice.get("delta") or {}
        text = msg.get("content") or ""
        if not text:
            continue
        events.append({
            **base,
            "event_id": _event_id(str(conv_id), ts_iso, f"resp_{i}"),
            "episode_id": "",
            "event_type": "response",
            "timestamp": ts_iso,
            "payload": text[:4000],
            "meta": {"role": "assistant", "model": model, "finish_reason": choice.get("finish_reason")},
        })

    # --- tool calls ---
    for choice in choices:
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        for j, tc in enumerate(tool_calls):
            fn = tc.get("function") or {}
            events.append({
                **base,
                "event_id": _event_id(str(conv_id), ts_iso, f"tool_{j}"),
                "episode_id": "",
                "event_type": "tool_call",
                "timestamp": ts_iso,
                "payload": json.dumps({"name": fn.get("name"), "arguments": fn.get("arguments")})[:4000],
                "meta": {"model": model},
            })

    # --- usage / metrics ---
    usage = entry.get("usage")
    if usage:
        events.append({
            **base,
            "event_id": _event_id(str(conv_id), ts_iso, "usage"),
            "episode_id": "",
            "event_type": "metric",
            "timestamp": ts_iso,
            "payload": json.dumps(usage),
            "meta": {"model": model},
        })

    return events


# ---------------------------------------------------------------------------
# Group events into episodes by (user_hash, conv_id, time_window)
# ---------------------------------------------------------------------------

def _group_events(
    events: List[Dict[str, Any]],
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group events into episode buckets."""
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for ev in sorted(events, key=lambda e: e.get("timestamp", "")):
        ts = _parse_ts(ev.get("timestamp", ""))
        # bucket key: user + session + time window
        window_key = ts.strftime("%Y%m%d%H") + str(ts.minute // window_minutes)
        key = f"{ev.get('user_hash', 'anon')}|{ev.get('session_id', '')}|{window_key}"
        episode_id = hashlib.sha256(key.encode()).hexdigest()[:24]
        ev["episode_id"] = episode_id
        buckets[episode_id].append(ev)

    return dict(buckets)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_openai_logs(
    input_path: str,
    endpoint: str = DEFAULT_ENDPOINT,
    project: Optional[str] = None,
    team: Optional[str] = None,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Read a JSONL file of OpenAI/Azure logs, normalise, group, and POST.

    Returns summary dict with counts.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    all_events: List[Dict[str, Any]] = []

    with open(path, "r") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping line %d: %s", line_no, exc)
                continue

            if project:
                entry.setdefault("project", project)
            if team:
                entry.setdefault("team", team)

            events = _normalise_entry(entry)
            all_events.extend(events)

    grouped = _group_events(all_events, window_minutes)

    summary = {
        "input_file": str(path),
        "total_events": len(all_events),
        "episodes": len(grouped),
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("Dry run: %d events in %d episodes", len(all_events), len(grouped))
        return summary

    # POST all events in one batch
    try:
        import urllib.request

        data = json.dumps(all_events).encode()
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            summary["api_response"] = body
    except Exception as exc:
        logger.error("POST failed: %s", exc)
        summary["error"] = str(exc)

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest OpenAI / Azure OpenAI logs into Exhaust Inbox",
    )
    parser.add_argument("--input", "-i", required=True, help="Path to JSONL log file")
    parser.add_argument("--endpoint", "-e", default=DEFAULT_ENDPOINT, help="Exhaust API endpoint")
    parser.add_argument("--project", "-p", default=None, help="Project tag")
    parser.add_argument("--team", "-t", default=None, help="Team tag")
    parser.add_argument("--window", "-w", type=int, default=DEFAULT_WINDOW_MINUTES, help="Grouping window (minutes)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and group but do not POST")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = ingest_openai_logs(
        input_path=args.input,
        endpoint=args.endpoint,
        project=args.project,
        team=args.team,
        window_minutes=args.window,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
