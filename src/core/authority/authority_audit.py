"""Authority Audit — hash-chained append-only audit log.

Follows the same hash-chain pattern as AuthorityLedger in ledger.py.
Every authority evaluation is recorded with a tamper-evident chain.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AuditRecord
from .seal_and_hash import compute_hash as _compute_hash

logger = logging.getLogger(__name__)


class AuthorityAuditLog:
    """Hash-chained audit log for AuthorityOps evaluations.

    Usage::

        log = AuthorityAuditLog(path=Path("authority_audit.json"))
        chain_hash = log.append(AuditRecord(...))
        assert log.verify_chain()
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._records: List[AuditRecord] = []
        self._path = path
        if self._path is not None and self._path.exists():
            self._load()

    @property
    def records(self) -> List[AuditRecord]:
        return list(self._records)

    @property
    def record_count(self) -> int:
        return len(self._records)

    def append(self, record: AuditRecord) -> str:
        """Hash-chain and append an audit record. Returns the chain_hash."""
        record.prev_chain_hash = (
            self._records[-1].chain_hash if self._records else None
        )
        record.evaluated_at = record.evaluated_at or datetime.now(timezone.utc).isoformat()
        if not record.audit_id:
            record.audit_id = f"AUDIT-{uuid.uuid4().hex[:12]}"

        # Compute chain hash over record content (excluding chain_hash itself)
        hashable = asdict(record)
        hashable["chain_hash"] = ""
        record.chain_hash = _compute_hash(hashable)

        self._records.append(record)
        self._persist()
        return record.chain_hash

    def verify_chain(self) -> bool:
        """Walk the chain and verify every hash. Returns True if valid."""
        for i, record in enumerate(self._records):
            if i == 0:
                if record.prev_chain_hash is not None:
                    return False
            else:
                if record.prev_chain_hash != self._records[i - 1].chain_hash:
                    return False
            hashable = asdict(record)
            hashable["chain_hash"] = ""
            expected = _compute_hash(hashable)
            if record.chain_hash != expected:
                return False
        return True

    def query_by_action(self, action_id: str) -> List[AuditRecord]:
        """Find all audit records for a given action."""
        return [r for r in self._records if r.action_id == action_id]

    def query_by_actor(self, actor_id: str) -> List[AuditRecord]:
        """Find all audit records for a given actor."""
        return [r for r in self._records if r.actor_id == actor_id]

    def query_by_verdict(self, verdict: str) -> List[AuditRecord]:
        """Find all audit records with a given verdict."""
        return [r for r in self._records if r.verdict == verdict]

    # -- Persistence --

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(r) for r in self._records]
        self._path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        raw = self._path.read_text(encoding="utf-8").strip()
        if not raw:
            return
        records = json.loads(raw)
        if not isinstance(records, list):
            raise ValueError("Authority audit log must be a JSON array")
        for item in records:
            self._records.append(
                AuditRecord(
                    **{
                        k: item[k]
                        for k in AuditRecord.__dataclass_fields__
                        if k in item
                    }
                )
            )
