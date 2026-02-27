"""Shared helpers for callback handlers and connectors."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


# ── Exhaust helpers ──────────────────────────────────────────────────────────

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


# ── Connector helpers ────────────────────────────────────────────────────────

def uuid_from_hash(prefix: str, raw_id: str) -> str:
    """Deterministic UUID v5-style from ``prefix`` and ``raw_id``."""
    digest = hashlib.sha256(f"{prefix}:{raw_id}".encode()).digest()[:16]
    return str(UUID(bytes=digest, version=4))


def to_iso(date_str: Optional[str]) -> str:
    """Normalize a date string to ISO-8601 UTC."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()

    # Epoch milliseconds
    if date_str.isdigit() and len(date_str) >= 13:
        try:
            return datetime.fromtimestamp(
                int(date_str) / 1000, tz=timezone.utc,
            ).isoformat()
        except (ValueError, OSError):
            pass

    # ISO-8601 variants
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass

    return ""


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(text: Optional[str]) -> str:
    """Remove HTML tags from text, collapsing whitespace."""
    if not text:
        return ""
    cleaned = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def verify_webhook_hmac(body: bytes, secret: str, signature: str) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
