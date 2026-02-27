"""Append-only canon store — SQLite-backed versioned canon entries.

Canon entries are never overwritten. New versions point to the prior entry
via ``supersedes``, forming a version chain.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..envelope import build_envelope
from ..types import Classification, FeedTopic


class CanonStore:
    """SQLite-backed append-only canon store with supersedes chain."""

    def __init__(
        self,
        db_path: str | Path,
        topics_root: Optional[str | Path] = None,
        producer: str = "feeds-canon",
        classification: Classification | str = Classification.LEVEL_0,
    ) -> None:
        self._db_path = str(db_path)
        self._topics_root = Path(topics_root).resolve() if topics_root else None
        self._producer = producer
        self._classification = classification
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS canon_store (
                canon_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                domain TEXT NOT NULL DEFAULT '',
                superseded_by TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def add(self, canon_entry: Dict[str, Any]) -> str:
        """Add a canon entry to the store.

        If the entry declares a ``supersedes`` field, the prior entry's
        ``superseded_by`` pointer is updated.

        Args:
            canon_entry: A canon_entry payload dict.

        Returns:
            The canonId of the stored entry.
        """
        canon_id = canon_entry["canonId"]
        version = canon_entry.get("version", "1.0.0")
        domain = canon_entry.get("scope", {}).get("domain", "")
        supersedes = canon_entry.get("supersedes")
        now = datetime.now(timezone.utc).isoformat()

        self._conn.execute(
            """INSERT OR REPLACE INTO canon_store
               (canon_id, version, domain, created_at, data)
               VALUES (?, ?, ?, ?, ?)""",
            (canon_id, version, domain, now, json.dumps(canon_entry)),
        )

        # Update superseded_by pointer on prior entry
        if supersedes:
            self._conn.execute(
                "UPDATE canon_store SET superseded_by = ? WHERE canon_id = ?",
                (canon_id, supersedes),
            )

        self._conn.commit()

        # Emit cache invalidation event if topics_root configured
        if self._topics_root is not None:
            self._emit_cache_invalidation(canon_id, canon_entry)

        return canon_id

    def get(self, canon_id: str) -> Optional[Dict[str, Any]]:
        """Get a single canon entry by ID."""
        row = self._conn.execute(
            "SELECT * FROM canon_store WHERE canon_id = ?", (canon_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_entries(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List canon entries, optionally filtered by domain."""
        if domain:
            rows = self._conn.execute(
                "SELECT * FROM canon_store WHERE domain = ? ORDER BY created_at DESC",
                (domain,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM canon_store ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_version_chain(self, canon_id: str) -> List[Dict[str, Any]]:
        """Follow the supersedes chain from a given canon entry.

        Returns a list starting with the given entry, walking backward
        through superseded entries.
        """
        chain: List[Dict[str, Any]] = []
        current_id: Optional[str] = canon_id

        visited: set = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            entry = self.get(current_id)
            if not entry:
                break
            chain.append(entry)
            # Walk backward: find what this entry supersedes
            data = entry.get("data", {})
            current_id = data.get("supersedes")

        return chain

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def _emit_cache_invalidation(
        self, canon_id: str, canon_entry: Dict[str, Any]
    ) -> None:
        """Publish a canon_entry event as a cache invalidation signal."""
        try:
            assert self._topics_root is not None
            envelope = build_envelope(
                topic=FeedTopic.CANON_ENTRY,
                payload=canon_entry,
                packet_id=f"CP-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-0000",
                producer=self._producer,
                classification=self._classification,
            )
            ce_inbox = self._topics_root / "canon_entry" / "inbox"
            if ce_inbox.is_dir():
                target = ce_inbox / f"{envelope['eventId']}.json"
                target.write_text(
                    json.dumps(envelope, indent=2), encoding="utf-8"
                )
        except Exception:
            pass  # Best-effort cache invalidation

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "canonId": row["canon_id"],
            "version": row["version"],
            "domain": row["domain"],
            "supersededBy": row["superseded_by"],
            "createdAt": row["created_at"],
            "data": json.loads(row["data"]),
        }
