"""Shared helpers for connector adapters.

Provides deterministic UUIDs, date normalization, HTML stripping, and
webhook HMAC verification used across SharePoint, Power Platform,
Snowflake, and other connectors.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


def uuid_from_hash(prefix: str, raw_id: str) -> str:
    """Deterministic UUID v5-style from ``prefix`` and ``raw_id``.

    Uses SHA-256 truncated to 128 bits, formatted as a UUID string.
    Identical inputs always produce identical outputs.

    >>> uuid_from_hash("sp", "12345")
    '5f3a7c28-...'
    """
    digest = hashlib.sha256(f"{prefix}:{raw_id}".encode()).digest()[:16]
    return str(UUID(bytes=digest, version=4))


def to_iso(date_str: Optional[str]) -> str:
    """Normalize a date string to ISO-8601 UTC.

    Handles common formats: ISO-8601 with/without timezone,
    Microsoft Graph date strings, epoch milliseconds.
    Returns empty string on failure.
    """
    if not date_str:
        return ""
    date_str = str(date_str).strip()

    # Epoch milliseconds (all digits, > year 2000 in ms)
    if date_str.isdigit() and len(date_str) >= 13:
        try:
            return datetime.fromtimestamp(int(date_str) / 1000, tz=timezone.utc).isoformat()
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
    """Verify HMAC-SHA256 webhook signature.

    Parameters
    ----------
    body : bytes
        Raw request body.
    secret : str
        Shared HMAC secret.
    signature : str
        Hex-encoded HMAC signature from the request header.
    """
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
