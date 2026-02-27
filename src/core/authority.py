"""Authority Ledger — hash-chained record of who authorized what.

Core simplified version: no HMAC signing, no tier enforcement.
Same hash-chain integrity as enterprise, suitable for the open-source
agent decision logging use case.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LEDGER_SCHEMA_VERSION = "authority-ledger-core-v1"


def _canonical_json(payload: dict) -> str:
    """Deterministic JSON for hashing (matches enterprise pattern)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _compute_hash(payload: dict) -> str:
    """SHA-256 of canonical JSON. Returns ``sha256:<hex>`` string."""
    digest = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


@dataclass
class AuthorityEntry:
    """A single entry in the authority ledger."""

    entry_id: str
    entry_type: str  # "grant" | "revocation" | "snapshot"
    authority_source: str
    authority_role: str
    scope: str
    claims_blessed: List[str]
    effective_at: str
    expires_at: Optional[str]
    entry_hash: str
    prev_entry_hash: Optional[str]
    recorded_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuthorityLedger:
    """Hash-chained authority ledger with JSON persistence.

    Usage::

        ledger = AuthorityLedger(path=Path("authority_ledger.json"))
        entry_hash = ledger.append(AuthorityEntry(...))
        assert ledger.verify_chain()
        proof = ledger.prove_authority("CLAIM-2026-0001")
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._entries: List[AuthorityEntry] = []
        self._path: Optional[Path] = path
        if self._path is not None and self._path.exists():
            self._load()

    @property
    def entries(self) -> List[AuthorityEntry]:
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def append(self, entry: AuthorityEntry) -> str:
        """Hash-chain and append an entry. Returns the entry_hash."""
        entry.prev_entry_hash = (
            self._entries[-1].entry_hash if self._entries else None
        )
        entry.recorded_at = datetime.now(timezone.utc).isoformat()
        if not entry.entry_id:
            entry.entry_id = f"AUTH-{uuid.uuid4().hex[:12]}"

        # Compute hash over entry content (excluding entry_hash itself)
        hashable = asdict(entry)
        hashable["entry_hash"] = ""
        entry.entry_hash = _compute_hash(hashable)

        self._entries.append(entry)
        self._persist()
        return entry.entry_hash

    def snapshot(self) -> dict:
        """Current ledger state summary."""
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "entry_count": len(self._entries),
            "latest_entry_hash": (
                self._entries[-1].entry_hash if self._entries else None
            ),
            "ledger_hash": _compute_hash(
                {"entries": [asdict(e) for e in self._entries]}
            ),
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }

    def verify_chain(self) -> bool:
        """Walk the chain and verify every hash. Returns True if valid."""
        for i, entry in enumerate(self._entries):
            # Verify prev_entry_hash link
            if i == 0:
                if entry.prev_entry_hash is not None:
                    return False
            else:
                if entry.prev_entry_hash != self._entries[i - 1].entry_hash:
                    return False
            # Verify entry_hash
            hashable = asdict(entry)
            hashable["entry_hash"] = ""
            expected = _compute_hash(hashable)
            if entry.entry_hash != expected:
                return False
        return True

    def prove_authority(self, claim_id: str) -> Optional[dict]:
        """Find the most recent grant that blesses a claim.

        Returns proof dict or None.
        """
        for entry in reversed(self._entries):
            if (
                entry.entry_type == "revocation"
                and claim_id in entry.claims_blessed
            ):
                return None
            if (
                entry.entry_type == "grant"
                and claim_id in entry.claims_blessed
            ):
                return {
                    "claim_id": claim_id,
                    "entry_id": entry.entry_id,
                    "authority_source": entry.authority_source,
                    "authority_role": entry.authority_role,
                    "scope": entry.scope,
                    "effective_at": entry.effective_at,
                    "expires_at": entry.expires_at,
                    "entry_hash": entry.entry_hash,
                    "chain_valid": self.verify_chain(),
                }
        return None

    def to_authority_slice(self) -> dict:
        """Export current blessed claims as a FEEDS ALS-compatible payload."""
        blessed: set = set()
        for entry in self._entries:
            if entry.entry_type == "grant":
                blessed.update(entry.claims_blessed)
            elif entry.entry_type == "revocation":
                blessed.difference_update(entry.claims_blessed)

        latest = self._entries[-1] if self._entries else None
        now = datetime.now(timezone.utc).isoformat()
        return {
            "sliceId": f"ALS-ledger-{uuid.uuid4().hex[:8]}",
            "authoritySource": (
                latest.authority_source if latest else "unknown"
            ),
            "authorityRole": latest.authority_role if latest else "unknown",
            "scope": latest.scope if latest else "global",
            "claimsBlessed": sorted(blessed),
            "effectiveAt": latest.effective_at if latest else now,
            "seal": {
                "hash": self.snapshot()["ledger_hash"],
                "sealedAt": now,
                "version": 1,
            },
        }

    # -- Persistence --

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self._entries]
        self._path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        raw = self._path.read_text(encoding="utf-8").strip()
        if not raw:
            return
        entries = json.loads(raw)
        if not isinstance(entries, list):
            raise ValueError("Authority ledger must be a JSON array")
        for item in entries:
            self._entries.append(
                AuthorityEntry(
                    **{
                        k: item[k]
                        for k in AuthorityEntry.__dataclass_fields__
                        if k in item
                    }
                )
            )
