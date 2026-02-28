"""Non-coercion audit logger — append-only, hash-chained NDJSON.

Each entry is linked to the previous via a SHA-256 chain hash,
ensuring tamper-evidence for the non-coercion audit trail.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class AuditEntry:
    """A single audit log entry."""

    def __init__(
        self,
        entry_type: str,
        episode_id: str = "",
        function_id: str = "",
        detail: str = "",
        actor: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.entry_type = entry_type
        self.episode_id = episode_id
        self.function_id = function_id
        self.detail = detail
        self.actor = actor
        self.metadata = metadata or {}
        self.chain_hash = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "entryType": self.entry_type,
            "episodeId": self.episode_id,
            "functionId": self.function_id,
            "detail": self.detail,
            "actor": self.actor,
            "metadata": self.metadata,
            "chainHash": self.chain_hash,
        }


class AuditLog:
    """In-memory append-only audit log with hash chaining."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._last_hash: str = "sha256:genesis"

    def append(self, entry: AuditEntry) -> str:
        """Append an entry to the log. Returns the chain hash."""
        content = json.dumps({
            "prev": self._last_hash,
            "timestamp": entry.timestamp,
            "entryType": entry.entry_type,
            "episodeId": entry.episode_id,
            "functionId": entry.function_id,
            "detail": entry.detail,
        }, sort_keys=True, separators=(",", ":"))

        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        entry.chain_hash = f"sha256:{digest}"
        self._last_hash = entry.chain_hash

        self._entries.append(entry)
        return entry.chain_hash

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def entries(self) -> List[Dict[str, Any]]:
        """Return all entries as dicts."""
        return [e.to_dict() for e in self._entries]

    def verify_chain(self) -> bool:
        """Verify the hash chain integrity. Returns True if valid."""
        prev = "sha256:genesis"
        for entry in self._entries:
            content = json.dumps({
                "prev": prev,
                "timestamp": entry.timestamp,
                "entryType": entry.entry_type,
                "episodeId": entry.episode_id,
                "functionId": entry.function_id,
                "detail": entry.detail,
            }, sort_keys=True, separators=(",", ":"))
            expected = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
            if entry.chain_hash != expected:
                return False
            prev = entry.chain_hash
        return True
