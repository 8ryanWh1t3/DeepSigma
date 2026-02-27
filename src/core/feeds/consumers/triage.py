"""Drift triage store — SQLite-backed state machine for drift signal lifecycle.

States: NEW -> TRIAGED -> PATCH_PLANNED -> PATCHED -> VERIFIED

Invalid transitions raise ``ValueError``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TriageState(str, Enum):
    """Drift triage lifecycle states."""

    NEW = "NEW"
    TRIAGED = "TRIAGED"
    PATCH_PLANNED = "PATCH_PLANNED"
    PATCHED = "PATCHED"
    VERIFIED = "VERIFIED"


# Valid forward transitions
_TRANSITIONS: Dict[TriageState, List[TriageState]] = {
    TriageState.NEW: [TriageState.TRIAGED],
    TriageState.TRIAGED: [TriageState.PATCH_PLANNED],
    TriageState.PATCH_PLANNED: [TriageState.PATCHED],
    TriageState.PATCHED: [TriageState.VERIFIED],
    TriageState.VERIFIED: [],
}


@dataclass
class TriageEntry:
    """A single drift triage record."""

    drift_id: str
    state: TriageState
    severity: str
    drift_type: str
    packet_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


class TriageStore:
    """SQLite-backed drift triage store with enforced state transitions."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS drift_triage (
                drift_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                severity TEXT NOT NULL,
                drift_type TEXT NOT NULL,
                packet_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                notes TEXT DEFAULT '',
                data TEXT DEFAULT '{}'
            )
        """)
        self._conn.commit()

    def ingest_drift(self, drift_event: Dict[str, Any]) -> TriageEntry:
        """Create a NEW triage entry from a drift signal event.

        Args:
            drift_event: A FEEDS drift signal event (full envelope or payload).

        Returns:
            The created TriageEntry.
        """
        payload = drift_event.get("payload", drift_event)
        now = datetime.now(timezone.utc).isoformat()

        entry = TriageEntry(
            drift_id=payload.get("driftId", ""),
            state=TriageState.NEW,
            severity=payload.get("severity", "yellow"),
            drift_type=payload.get("driftType", ""),
            packet_id=drift_event.get("packetId", ""),
            created_at=now,
            updated_at=now,
            notes=payload.get("notes", ""),
            data=payload,
        )

        self._conn.execute(
            """INSERT OR REPLACE INTO drift_triage
               (drift_id, state, severity, drift_type, packet_id,
                created_at, updated_at, notes, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.drift_id,
                entry.state.value,
                entry.severity,
                entry.drift_type,
                entry.packet_id,
                entry.created_at,
                entry.updated_at,
                entry.notes,
                json.dumps(entry.data),
            ),
        )
        self._conn.commit()
        return entry

    def set_state(
        self, drift_id: str, new_state: TriageState | str, notes: str = ""
    ) -> TriageEntry:
        """Transition a triage entry to a new state.

        Args:
            drift_id: The drift signal ID.
            new_state: Target state.
            notes: Optional notes for this transition.

        Returns:
            The updated TriageEntry.

        Raises:
            KeyError: If drift_id not found.
            ValueError: If transition is invalid.
        """
        if isinstance(new_state, str):
            new_state = TriageState(new_state)

        row = self._conn.execute(
            "SELECT * FROM drift_triage WHERE drift_id = ?", (drift_id,)
        ).fetchone()

        if row is None:
            raise KeyError(f"Drift ID not found: {drift_id}")

        current = TriageState(row["state"])
        allowed = _TRANSITIONS.get(current, [])

        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {current.value} -> {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        now = datetime.now(timezone.utc).isoformat()
        combined_notes = row["notes"]
        if notes:
            combined_notes = f"{combined_notes}\n{notes}".strip() if combined_notes else notes

        self._conn.execute(
            """UPDATE drift_triage
               SET state = ?, updated_at = ?, notes = ?
               WHERE drift_id = ?""",
            (new_state.value, now, combined_notes, drift_id),
        )
        self._conn.commit()

        return self._row_to_entry(
            self._conn.execute(
                "SELECT * FROM drift_triage WHERE drift_id = ?", (drift_id,)
            ).fetchone()
        )

    def get(self, drift_id: str) -> Optional[TriageEntry]:
        """Get a single triage entry by drift ID."""
        row = self._conn.execute(
            "SELECT * FROM drift_triage WHERE drift_id = ?", (drift_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def list_entries(
        self, state: Optional[TriageState | str] = None, limit: int = 50
    ) -> List[TriageEntry]:
        """List triage entries, optionally filtered by state."""
        if state is not None:
            state_val = state.value if isinstance(state, TriageState) else state
            rows = self._conn.execute(
                "SELECT * FROM drift_triage WHERE state = ? ORDER BY updated_at DESC LIMIT ?",
                (state_val, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM drift_triage ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics."""
        rows = self._conn.execute(
            "SELECT state, COUNT(*) as cnt FROM drift_triage GROUP BY state"
        ).fetchall()
        by_state = {r["state"]: r["cnt"] for r in rows}

        sev_rows = self._conn.execute(
            "SELECT severity, COUNT(*) as cnt FROM drift_triage GROUP BY severity"
        ).fetchall()
        by_severity = {r["severity"]: r["cnt"] for r in sev_rows}

        total = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM drift_triage"
        ).fetchone()["cnt"]

        return {
            "by_state": by_state,
            "by_severity": by_severity,
            "total": total,
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> TriageEntry:
        return TriageEntry(
            drift_id=row["drift_id"],
            state=TriageState(row["state"]),
            severity=row["severity"],
            drift_type=row["drift_type"],
            packet_id=row["packet_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            notes=row["notes"],
            data=json.loads(row["data"]),
        )
