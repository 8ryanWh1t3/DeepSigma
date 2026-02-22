"""Mesh Logstore — Append-only JSONL with atomic writes.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

_write_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_path(path: str | Path) -> Path:
    raw = Path(path)
    if any(part == ".." for part in raw.parts):
        raise ValueError("Path traversal is not allowed")
    candidate = raw.expanduser().resolve()
    return candidate


def append_jsonl(path: str | Path, record: dict) -> None:
    """Atomically append a JSON record to a JSONL file.

    Uses temp-file + rename for atomic write on append.
    """
    path = _normalize_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    record.setdefault("timestamp", _now_iso())
    line = json.dumps(record, default=str) + "\n"

    with _write_lock:
        # For append-only, we read existing content, append, write temp, rename.
        existing = b""
        if path.exists():
            existing = path.read_bytes()

        fd, tmp = tempfile.mkstemp(
            dir=str(path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(existing)
                f.write(line.encode("utf-8"))
            os.replace(tmp, str(path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def load_last_n(path: str | Path, n: int = 50) -> list[dict]:
    """Load the last N records from a JSONL file."""
    path = _normalize_path(path)
    if not path.exists():
        return []

    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                lines.append(raw)

    result = []
    for raw in lines[-n:]:
        try:
            result.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return result


def load_all(path: str | Path) -> list[dict]:
    """Load all records from a JSONL file."""
    path = _normalize_path(path)
    if not path.exists():
        return []

    result = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                try:
                    result.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    return result


def load_since(path: str | Path, iso_time: str) -> list[dict]:
    """Load records with timestamp >= iso_time."""
    all_records = load_all(path)
    return [
        r for r in all_records
        if r.get("timestamp", "") >= iso_time
    ]


def dedupe_by_id(records: list[dict], id_field: str) -> list[dict]:
    """Deduplicate records by a given ID field, keeping last occurrence."""
    seen: dict[str, dict] = {}
    for r in records:
        key = r.get(id_field, "")
        if key:
            seen[key] = r
    return list(seen.values())


def write_json(path: str | Path, data: dict) -> None:
    """Atomically write a single JSON file."""
    path = _normalize_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _write_lock:
        fd, tmp = tempfile.mkstemp(
            dir=str(path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.write("\n")
            os.replace(tmp, str(path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def load_json(path: str | Path) -> dict | None:
    """Load a single JSON file. Returns None if missing."""
    path = _normalize_path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
