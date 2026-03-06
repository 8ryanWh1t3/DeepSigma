"""Evidence Chain — Primitive 5: Append-Only Evidence Log.

Hash-chained JSONL evidence log capturing every authority evaluation
with full artifact and assumption context.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .seal_and_hash import compute_hash


@dataclass
class EvidenceEntry:
    """A single evidence record in the chain."""

    evidence_id: str
    gate_id: str
    action_id: str
    actor_id: str
    resource_id: str
    verdict: str  # AuthorityVerdict value
    evaluated_at: str
    artifact_id: str = ""
    policy_hash: str = ""
    dlr_ref: str = ""
    assumptions_snapshot: Dict[str, Any] = field(default_factory=dict)
    failed_checks: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    chain_hash: str = ""
    prev_chain_hash: Optional[str] = None


class EvidenceChain:
    """Append-only, hash-chained JSONL evidence log.

    Usage::

        chain = EvidenceChain(path=Path("evidence.jsonl"))
        entry = EvidenceEntry(...)
        chain_hash = chain.append(entry)
        assert chain.verify()
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._entries: List[EvidenceEntry] = []
        self._path = path
        if self._path is not None and self._path.exists():
            self._load()

    @property
    def entries(self) -> List[EvidenceEntry]:
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def append(self, entry: EvidenceEntry) -> str:
        """Hash-chain and append an evidence entry. Returns the chain_hash."""
        entry.prev_chain_hash = (
            self._entries[-1].chain_hash if self._entries else None
        )
        if not entry.evaluated_at:
            entry.evaluated_at = datetime.now(timezone.utc).isoformat()
        if not entry.evidence_id:
            entry.evidence_id = f"EV-{uuid.uuid4().hex[:12]}"

        # Compute chain hash (excluding chain_hash itself)
        hashable = asdict(entry)
        hashable["chain_hash"] = ""
        entry.chain_hash = compute_hash(hashable)

        self._entries.append(entry)
        self._persist()
        return entry.chain_hash

    def verify(self) -> bool:
        """Walk the chain and verify every hash link. Returns True if valid."""
        for i, entry in enumerate(self._entries):
            if i == 0:
                if entry.prev_chain_hash is not None:
                    return False
            else:
                if entry.prev_chain_hash != self._entries[i - 1].chain_hash:
                    return False
            hashable = asdict(entry)
            hashable["chain_hash"] = ""
            expected = compute_hash(hashable)
            if entry.chain_hash != expected:
                return False
        return True

    # -- Persistence (JSONL) --

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Append only the latest entry as a JSONL line
        latest = self._entries[-1]
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(latest), sort_keys=True) + "\n")

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").strip().splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            self._entries.append(
                EvidenceEntry(
                    **{
                        k: data[k]
                        for k in EvidenceEntry.__dataclass_fields__
                        if k in data
                    }
                )
            )
