#!/usr/bin/env python3
"""Deterministic ID generation — no random IDs in sealed artifacts.

IDs are derived from content hashes, not RNG. This ensures the same
inputs always produce the same IDs.
"""
from __future__ import annotations

from canonical_json import sha256_text


def det_id(prefix: str, canonical_payload_hash: str, length: int = 8) -> str:
    """Generate a deterministic ID from a content hash.

    Args:
        prefix: ID prefix (e.g. "RUN", "PX", "EVT")
        canonical_payload_hash: The sha256:... hash string to derive from
        length: Number of hex characters to use (default 8)

    Returns:
        Deterministic ID like "RUN-a1b2c3d4"
    """
    # Strip the "sha256:" prefix if present
    raw = canonical_payload_hash
    if raw.startswith("sha256:"):
        raw = raw[7:]
    return f"{prefix}-{raw[:length]}"


def det_id_from_payload(prefix: str, payload: str, length: int = 8) -> str:
    """Generate a deterministic ID by hashing a payload string.

    Args:
        prefix: ID prefix (e.g. "RUN", "PX", "EVT")
        payload: The raw string to hash
        length: Number of hex characters to use (default 8)

    Returns:
        Deterministic ID like "RUN-a1b2c3d4"
    """
    h = sha256_text(payload)
    return det_id(prefix, h, length)
