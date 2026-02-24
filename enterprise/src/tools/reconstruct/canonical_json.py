#!/usr/bin/env python3
"""Canonical JSON serialization for deterministic hashing.

ALL hashes in the system must be computed over canonical serialization only.
This ensures same inputs -> same bytes -> same hash, regardless of dict
ordering, whitespace, or float formatting.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


def _normalize_value(obj: object) -> object:
    """Recursively normalize a value for canonical serialization."""
    if isinstance(obj, dict):
        return {k: _normalize_value(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_normalize_value(v) for v in obj]
    if isinstance(obj, set):
        return sorted(_normalize_value(v) for v in obj)
    if isinstance(obj, float):
        # Normalize floats: strip trailing zeros, use fixed notation
        if obj == int(obj) and not (obj != obj):  # not NaN
            return int(obj)
        return float(f"{obj:.15g}")
    if isinstance(obj, str):
        # Normalize datetime strings to UTC ISO8601 with Z
        s = _normalize_datetime_string(obj)
        # Normalize newlines
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        return s
    return obj


def _normalize_datetime_string(s: str) -> str:
    """If a string looks like an ISO datetime, normalize to UTC Z format."""
    # Match common ISO datetime patterns
    iso_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        r"(?:\.\d+)?"
        r"(?:Z|[+-]\d{2}:\d{2})?$"
    )
    if not iso_pattern.match(s):
        return s
    try:
        # Try parsing with timezone
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError):
        return s


def canonical_dumps(obj: object) -> str:
    """Produce canonical JSON: sorted keys, compact separators, no trailing spaces."""
    normalized = _normalize_value(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_bytes(b: bytes) -> str:
    """SHA-256 hash of raw bytes."""
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    """SHA-256 hash of a UTF-8 string."""
    return sha256_bytes(s.encode("utf-8"))


def sha256_canonical(obj: object) -> str:
    """SHA-256 hash of the canonical JSON serialization of an object."""
    return sha256_text(canonical_dumps(obj))
