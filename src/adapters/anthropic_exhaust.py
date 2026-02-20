"""
adapters/anthropic_exhaust.py – Anthropic Messages API log ingestion adapter
=============================================================================
Batch ingestion of Anthropic Messages API response logs into the Exhaust
Inbox system.  Reads JSONL log files (one API response per line), normalises
them to EpisodeEvent payloads, groups by session_id + time window (30 min
default), and POSTs to the ingestion endpoint.

Usage (CLI):
    python -m adapters.anthropic_exhaust \
        --file /path/to/anthropic_logs.jsonl \
        --endpoint http://localhost:8000/api/exhaust/events \
        --dry-run

Usage (library):
    from adapters.anthropic_exhaust import ingest_anthropic_logs
    ingest_anthropic_logs("logs.jsonl", endpoint="http://localhost:8000/api/exhaust/events")

Expected log entry format (one Anthropic Messages API response per line):
    {
      "id": "msg_01abc...",
      "model": "claude-haiku-4-5-20251001",
      "session_id": "sess-001",          # optional; falls back to id
      "user_id": "user@example.com",     # optional; hashed for PII safety
      "input": [                         # input messages
        {"role": "user", "content": "What is the status?"}
      ],
      "content": [                       # response content blocks
        {"type": "text", "text": "Service is healthy."}
      ],
      "usage": {"input_tokens": 12, "output_tokens": 8},
      "stop_reason": "end_turn",
      "created_at": "2026-01-01T00:00:00Z",
      "project": "my-project",
      "team": "ml-ops"
    }
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
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
SOURCE = "anthropic"

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
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _text_from_content(content: Any) -> str:
    """Extract text from a content field that may be a string or list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


# ---------------------------------------------------------------------------
# Normalise a single Anthropic log entry → list of EpisodeEvent dicts
# ---------------------------------------------------------------------------


def _normalise_entry(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert one Anthropic Messages API log entry to EpisodeEvent dicts.

    Produces:
      - prompt events for each input message
      - completion event for text content blocks
      - tool events for tool_use content blocks
      - metric event for usage stats
    """
    events: List[Dict[str, Any]] = []

    ts_raw = entry.get("created_at") or entry.get("timestamp") or _utcnow()
    ts = _parse_ts(ts_raw)
    ts_iso = ts.isoformat()

    user_raw = entry.get("user_id") or entry.get("user") or ""
    user_hash = _hash(str(user_raw)) if user_raw else "anon"

    session_id = (
        entry.get("session_id")
        or entry.get("conversation_id")
        or entry.get("id")
        or ""
    )

    model = entry.get("model", "unknown")
    project = entry.get("project") or entry.get("metadata", {}).get("project") or "default"
    team = entry.get("team") or entry.get("metadata", {}).get("team") or ""

    base = {
        "session_id": str(session_id),
        "user_hash": user_hash,
        "source": SOURCE,
        "project": project,
        "team": team,
        "episode_id": "",
    }

    # ── Input messages → prompt events ───────────────────────────────────
    input_messages = entry.get("input") or entry.get("messages") or []
    for i, msg in enumerate(input_messages):
        role = msg.get("role", "user")
        text = _text_from_content(msg.get("content", ""))
        events.append({
            **base,
            "event_id": _event_id(str(session_id), ts_iso, f"in_{i}"),
            "event_type": "prompt",
            "timestamp": ts_iso,
            "payload": {"text": text[:4000], "role": role},
        })

    # ── Output content blocks → completion / tool events ─────────────────
    content_blocks = entry.get("content") or []
    for i, block in enumerate(content_blocks):
        btype = block.get("type", "text")
        if btype == "text":
            events.append({
                **base,
                "event_id": _event_id(str(session_id), ts_iso, f"out_{i}"),
                "event_type": "completion",
                "timestamp": ts_iso,
                "payload": {
                    "text": block.get("text", "")[:4000],
                    "role": "assistant",
                    "model": model,
                    "stop_reason": entry.get("stop_reason", ""),
                },
            })
        elif btype == "tool_use":
            events.append({
                **base,
                "event_id": _event_id(str(session_id), ts_iso, f"tool_{i}"),
                "event_type": "tool",
                "timestamp": ts_iso,
                "payload": {
                    "name": block.get("name", ""),
                    "input": block.get("input") or {},
                },
            })

    # ── Usage → metric event ──────────────────────────────────────────────
    usage = entry.get("usage") or {}
    if usage:
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        events.append({
            **base,
            "event_id": _event_id(str(session_id), ts_iso, "metric"),
            "event_type": "metric",
            "timestamp": ts_iso,
            "payload": {
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
                "model": model,
            },
        })

    return events


# ---------------------------------------------------------------------------
# Group events into episodes
# ---------------------------------------------------------------------------


def _group_events(
    events: List[Dict[str, Any]],
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group events into episode buckets by (user_hash, session_id, time_window)."""
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ev in sorted(events, key=lambda e: e.get("timestamp", "")):
        ts = _parse_ts(ev.get("timestamp", ""))
        window_key = ts.strftime("%Y%m%d%H") + str(ts.minute // max(window_minutes, 1))
        key = f"{ev.get('user_hash', 'anon')}|{ev.get('session_id', '')}|{window_key}"
        episode_id = hashlib.sha256(key.encode()).hexdigest()[:24]
        ev["episode_id"] = episode_id
        buckets[episode_id].append(ev)
    return dict(buckets)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_anthropic_logs(
    file_path: str,
    endpoint: str = DEFAULT_ENDPOINT,
    project: Optional[str] = None,
    team: Optional[str] = None,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Read Anthropic JSONL logs, normalise, group, and POST to Exhaust Inbox.

    Returns a summary dict with counts.
    """
    path = Path(file_path)
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

            all_events.extend(_normalise_entry(entry))

    grouped = _group_events(all_events, window_minutes)

    summary: Dict[str, Any] = {
        "input_file": str(path),
        "total_events": len(all_events),
        "episodes": len(grouped),
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("Dry run: %d events in %d episodes", len(all_events), len(grouped))
        return summary

    import urllib.request

    posted, errors = 0, 0
    for ev in all_events:
        data = json.dumps(ev).encode()
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 400:
                    posted += 1
                else:
                    errors += 1
        except Exception as exc:
            logger.warning("POST failed for event %s: %s", ev.get("event_id"), exc)
            errors += 1

    summary["posted"] = posted
    summary["errors"] = errors
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest Anthropic Messages API logs into Exhaust Inbox",
    )
    parser.add_argument("--file", "-f", required=True, help="Path to Anthropic JSONL log file")
    parser.add_argument("--endpoint", "-e", default=DEFAULT_ENDPOINT, help="Exhaust API endpoint")
    parser.add_argument("--project", "-p", default=None, help="Project tag")
    parser.add_argument("--team", "-t", default=None, help="Team tag")
    parser.add_argument(
        "--window", "-w", type=int, default=DEFAULT_WINDOW_MINUTES,
        help="Session grouping window in minutes",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and group without POSTing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = ingest_anthropic_logs(
        file_path=args.file,
        endpoint=args.endpoint,
        project=args.project,
        team=args.team,
        window_minutes=args.window,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
