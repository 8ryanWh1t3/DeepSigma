"""Storage backend abstraction for DeepSigma evidence persistence.

Provides a unified interface for storing events, episodes, drift records,
and decision log records (DLRs). Implementations:
  - JSONLStorageBackend: file-based (backward compat, zero deps)
  - SQLiteStorageBackend: stdlib sqlite3 (dev/testing)
  - PostgreSQLStorageBackend: psycopg (production)

Usage:
    from core.storage import create_backend
    backend = create_backend("sqlite:///data/deepsigma.db")
    backend.append_event({"event_id": "e1", ...})
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .normalize import normalize_keys

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract interface for evidence persistence."""

    # -- Events (append-only) --

    @abstractmethod
    def append_event(self, event: Dict[str, Any]) -> None:
        """Append a raw event."""
        ...

    @abstractmethod
    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List events with pagination."""
        ...

    # -- Episodes --

    @abstractmethod
    def save_episode(self, episode: Dict[str, Any]) -> None:
        """Save or update an episode."""
        ...

    @abstractmethod
    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Get a single episode by ID."""
        ...

    @abstractmethod
    def list_episodes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List episodes with pagination."""
        ...

    # -- Drift (append-only) --

    @abstractmethod
    def append_drift(self, drift: Dict[str, Any]) -> None:
        """Append a drift event."""
        ...

    @abstractmethod
    def list_drifts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List drift events with pagination."""
        ...

    # -- DLRs --

    @abstractmethod
    def save_dlr(self, dlr: Dict[str, Any]) -> None:
        """Save or update a Decision Log Record."""
        ...

    @abstractmethod
    def get_dlr(self, dlr_id: str) -> Optional[Dict[str, Any]]:
        """Get a single DLR by ID."""
        ...

    @abstractmethod
    def list_dlrs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List DLRs with pagination."""
        ...


# ---------------------------------------------------------------------------
# SQLite implementation
# ---------------------------------------------------------------------------

_SQLITE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    event_type TEXT,
    timestamp TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    decision_type TEXT,
    sealed_at TEXT,
    outcome_code TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drift_id TEXT UNIQUE,
    episode_id TEXT,
    drift_type TEXT,
    severity TEXT,
    detected_at TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dlrs (
    dlr_id TEXT PRIMARY KEY,
    episode_id TEXT,
    decision_type TEXT,
    recorded_at TEXT,
    outcome_code TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
"""


class SQLiteStorageBackend(StorageBackend):
    """SQLite-based storage using stdlib sqlite3."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        parent = Path(self._db_path).parent
        if str(parent) != "." and str(parent) != ":memory:":
            parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SQLITE_SCHEMA)
        self._conn.commit()

    # -- Events --

    def append_event(self, event: Dict[str, Any]) -> None:
        data = json.dumps(event, default=str)
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO events (event_id, event_type, timestamp, data) "
                "VALUES (?, ?, ?, ?)",
                (event.get("event_id"), event.get("event_type"),
                 event.get("timestamp"), data),
            )
            self._conn.commit()

    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT data FROM events ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    # -- Episodes --

    def save_episode(self, episode: Dict[str, Any]) -> None:
        episode = normalize_keys(episode)
        data = json.dumps(episode, default=str)
        ep_id = episode.get("episodeId", "")
        outcome = episode.get("outcome", {})
        outcome_code = outcome.get("code") if isinstance(outcome, dict) else None
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO episodes "
                "(episode_id, decision_type, sealed_at, outcome_code, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (ep_id, episode.get("decisionType"),
                 episode.get("sealedAt"),
                 outcome_code,
                 data),
            )
            self._conn.commit()

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT data FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list_episodes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT data FROM episodes ORDER BY sealed_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    # -- Drift --

    def append_drift(self, drift: Dict[str, Any]) -> None:
        drift = normalize_keys(drift)
        data = json.dumps(drift, default=str)
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO drifts "
                "(drift_id, episode_id, drift_type, severity, detected_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (drift.get("driftId"),
                 drift.get("episodeId"),
                 drift.get("driftType"),
                 drift.get("severity"),
                 drift.get("detectedAt"),
                 data),
            )
            self._conn.commit()

    def list_drifts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT data FROM drifts ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    # -- DLRs --

    def save_dlr(self, dlr: Dict[str, Any]) -> None:
        dlr = normalize_keys(dlr)
        data = json.dumps(dlr, default=str)
        dlr_id = dlr.get("dlrId", "")
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO dlrs "
                "(dlr_id, episode_id, decision_type, recorded_at, outcome_code, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (dlr_id,
                 dlr.get("episodeId"),
                 dlr.get("decisionType"),
                 dlr.get("recordedAt"),
                 dlr.get("outcomeCode"),
                 data),
            )
            self._conn.commit()

    def get_dlr(self, dlr_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT data FROM dlrs WHERE dlr_id = ?", (dlr_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list_dlrs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT data FROM dlrs ORDER BY recorded_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# JSONL implementation (backward compat)
# ---------------------------------------------------------------------------

class JSONLStorageBackend(StorageBackend):
    """File-based JSONL storage backend."""

    def __init__(self, directory: str | Path) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _append_jsonl(self, filename: str, record: Dict[str, Any]) -> None:
        with self._lock:
            with open(self._dir / filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")

    def _read_jsonl(self, filename: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        path = self._dir / filename
        if not path.exists():
            return []
        lines = path.read_text().strip().split("\n")
        lines = [line for line in lines if line.strip()]
        lines.reverse()  # newest first
        page = lines[offset:offset + limit]
        results = []
        for line in page:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return results

    def _read_json_dir(self, subdir: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        d = self._dir / subdir
        if not d.exists():
            return []
        files = sorted(d.glob("*.json"), reverse=True)
        results = []
        for f in files[offset:offset + limit]:
            try:
                results.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                continue
        return results

    # -- Events --

    def append_event(self, event: Dict[str, Any]) -> None:
        self._append_jsonl("events.jsonl", event)

    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self._read_jsonl("events.jsonl", limit, offset)

    # -- Episodes --

    def save_episode(self, episode: Dict[str, Any]) -> None:
        episode = normalize_keys(episode)
        ep_id = episode.get("episodeId", "unknown")
        ep_dir = self._dir / "episodes"
        ep_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            (ep_dir / f"{ep_id}.json").write_text(
                json.dumps(episode, default=str, indent=2)
            )

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        path = self._dir / "episodes" / f"{episode_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def list_episodes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self._read_json_dir("episodes", limit, offset)

    # -- Drift --

    def append_drift(self, drift: Dict[str, Any]) -> None:
        self._append_jsonl("drift.jsonl", drift)

    def list_drifts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self._read_jsonl("drift.jsonl", limit, offset)

    # -- DLRs --

    def save_dlr(self, dlr: Dict[str, Any]) -> None:
        dlr = normalize_keys(dlr)
        dlr_id = dlr.get("dlrId", "unknown")
        dlr_dir = self._dir / "dlrs"
        dlr_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            (dlr_dir / f"{dlr_id}.json").write_text(
                json.dumps(dlr, default=str, indent=2)
            )

    def get_dlr(self, dlr_id: str) -> Optional[Dict[str, Any]]:
        path = self._dir / "dlrs" / f"{dlr_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def list_dlrs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self._read_json_dir("dlrs", limit, offset)

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# PostgreSQL implementation
# ---------------------------------------------------------------------------

_PG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_id TEXT UNIQUE,
    event_type TEXT,
    timestamp TEXT,
    data JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    decision_type TEXT,
    sealed_at TEXT,
    outcome_code TEXT,
    data JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS drifts (
    id SERIAL PRIMARY KEY,
    drift_id TEXT UNIQUE,
    episode_id TEXT,
    drift_type TEXT,
    severity TEXT,
    detected_at TEXT,
    data JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS dlrs (
    dlr_id TEXT PRIMARY KEY,
    episode_id TEXT,
    decision_type TEXT,
    recorded_at TEXT,
    outcome_code TEXT,
    data JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
"""


class PostgreSQLStorageBackend(StorageBackend):
    """PostgreSQL-based storage using psycopg with connection pooling.

    Requires: pip install 'deepsigma[postgresql]'
    """

    def __init__(self, conninfo: str) -> None:
        try:
            import psycopg
            import psycopg.pool
        except ImportError:
            raise ImportError(
                "psycopg is required for PostgreSQL backend: "
                "pip install 'deepsigma[postgresql]'"
            )
        self._pool = psycopg.pool.ConnectionPool(conninfo, min_size=1, max_size=4)
        with self._pool.connection() as conn:
            conn.execute(_PG_SCHEMA)
            conn.commit()

    # -- Events --

    def append_event(self, event: Dict[str, Any]) -> None:
        data = json.dumps(event, default=str)
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO events (event_id, event_type, timestamp, data) "
                "VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT (event_id) DO NOTHING",
                (event.get("event_id"), event.get("event_type"),
                 event.get("timestamp"), data),
            )
            conn.commit()

    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT data FROM events ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    # -- Episodes --

    def save_episode(self, episode: Dict[str, Any]) -> None:
        episode = normalize_keys(episode)
        data = json.dumps(episode, default=str)
        ep_id = episode.get("episodeId", "")
        outcome = episode.get("outcome", {})
        outcome_code = outcome.get("code") if isinstance(outcome, dict) else None
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO episodes (episode_id, decision_type, sealed_at, outcome_code, data) "
                "VALUES (%s, %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (episode_id) DO UPDATE SET "
                "decision_type=EXCLUDED.decision_type, sealed_at=EXCLUDED.sealed_at, "
                "outcome_code=EXCLUDED.outcome_code, data=EXCLUDED.data",
                (ep_id, episode.get("decisionType"),
                 episode.get("sealedAt"),
                 outcome_code, data),
            )
            conn.commit()

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT data FROM episodes WHERE episode_id = %s", (episode_id,)
            ).fetchone()
            if not row:
                return None
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])

    def list_episodes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT data FROM episodes ORDER BY sealed_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    # -- Drift --

    def append_drift(self, drift: Dict[str, Any]) -> None:
        drift = normalize_keys(drift)
        data = json.dumps(drift, default=str)
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO drifts (drift_id, episode_id, drift_type, severity, detected_at, data) "
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb) ON CONFLICT (drift_id) DO NOTHING",
                (drift.get("driftId"),
                 drift.get("episodeId"),
                 drift.get("driftType"),
                 drift.get("severity"),
                 drift.get("detectedAt"),
                 data),
            )
            conn.commit()

    def list_drifts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT data FROM drifts ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    # -- DLRs --

    def save_dlr(self, dlr: Dict[str, Any]) -> None:
        dlr = normalize_keys(dlr)
        data = json.dumps(dlr, default=str)
        dlr_id = dlr.get("dlrId", "")
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO dlrs (dlr_id, episode_id, decision_type, recorded_at, outcome_code, data) "
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (dlr_id) DO UPDATE SET "
                "episode_id=EXCLUDED.episode_id, decision_type=EXCLUDED.decision_type, "
                "recorded_at=EXCLUDED.recorded_at, outcome_code=EXCLUDED.outcome_code, "
                "data=EXCLUDED.data",
                (dlr_id,
                 dlr.get("episodeId"),
                 dlr.get("decisionType"),
                 dlr.get("recordedAt"),
                 dlr.get("outcomeCode"),
                 data),
            )
            conn.commit()

    def get_dlr(self, dlr_id: str) -> Optional[Dict[str, Any]]:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT data FROM dlrs WHERE dlr_id = %s", (dlr_id,)
            ).fetchone()
            if not row:
                return None
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])

    def list_dlrs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT data FROM dlrs ORDER BY recorded_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    def close(self) -> None:
        self._pool.close()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_backend(url: Optional[str] = None) -> StorageBackend:
    """Create a storage backend from a URL string.

    Supported schemes:
      - sqlite:///path/to/db.sqlite
      - postgresql://user:pass@host:port/dbname
      - jsonl:///path/to/dir  (or empty/None for default)

    Falls back to DEEPSIGMA_STORAGE_URL env var if url is None.
    """
    if url is None:
        url = os.environ.get("DEEPSIGMA_STORAGE_URL", "")

    if not url or url.startswith("jsonl://"):
        path = url.replace("jsonl://", "", 1) if url else "data"
        return JSONLStorageBackend(path)

    if url.startswith("sqlite://"):
        db_path = url.replace("sqlite:///", "", 1).replace("sqlite://", "", 1)
        return SQLiteStorageBackend(db_path)

    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return PostgreSQLStorageBackend(url)

    raise ValueError(f"Unsupported storage URL scheme: {url}")
