"""Governance — Immutable Audit Trail.

Append-only audit log for critical actions and governance events.
Each tenant has an isolated audit log under data/audit/{tenant_id}.jsonl.

Records are never mutated or deleted via code paths.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE_AUDIT_DIR = Path(__file__).parent.parent / "data" / "audit"
_audit_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _audit_path(tenant_id: str) -> Path:
    """Return the audit log file path for a tenant."""
    d = _BASE_AUDIT_DIR / tenant_id
    d.mkdir(parents=True, exist_ok=True)
    return d / "audit.jsonl"


def append_audit(tenant_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Append a single audit event. Returns the enriched event."""
    enriched = dict(event)
    enriched.setdefault("audit_id", f"AUD-{uuid.uuid4().hex[:12]}")
    enriched.setdefault("tenant_id", tenant_id)
    enriched.setdefault("timestamp", _now_iso())
    filepath = _audit_path(tenant_id)
    with _audit_lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(enriched, default=str) + "\n")
    return enriched


def audit_action(
    tenant_id: str,
    actor_user: str,
    actor_role: str,
    action: str,
    target_type: str,
    target_id: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create and persist a structured audit event."""
    event = {
        "actor_user": actor_user,
        "actor_role": actor_role,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "outcome": outcome,
        "metadata": metadata or {},
    }
    return append_audit(tenant_id, event)


def load_recent_audit(
    tenant_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Load the most recent audit events for a tenant."""
    filepath = _audit_path(tenant_id)
    if not filepath.exists():
        return []
    lines: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    return [json.loads(line) for line in lines[-limit:]]
