"""Shared helpers for LangChain and LangGraph exhaust adapters."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional


def _hash_user(user_id: Optional[str]) -> str:
    """One-way hash for PII-safe user identification."""
    if not user_id:
        return "anon"
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def _make_event_id(*parts: str) -> str:
    """Deterministic event ID from composite key parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(obj: Any, max_len: int = 4000) -> str:
    """Convert payload to a string, truncating if necessary."""
    if isinstance(obj, str):
        s = obj
    else:
        try:
            s = json.dumps(obj, default=str)
        except Exception:
            s = str(obj)
    return s[:max_len] if len(s) > max_len else s
