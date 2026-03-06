"""Seal & Hash — Primitive 7: Cryptographic Immutability.

Foundation module for deterministic hashing, sealing, and chain
verification. All other OpenPQL primitives import from here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def canonical_json(payload: dict) -> str:
    """Deterministic JSON for hashing (sorted keys, compact separators)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(payload: dict) -> str:
    """SHA-256 of canonical JSON. Returns ``sha256:<hex>``."""
    digest = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def seal(payload: dict, sealed_at: Optional[str] = None) -> dict:
    """Seal a payload with its hash and timestamp.

    Returns:
        ``{"hash": "sha256:...", "sealedAt": "...", "version": 1}``
    """
    if sealed_at is None:
        sealed_at = datetime.now(timezone.utc).isoformat()
    return {
        "hash": compute_hash(payload),
        "sealedAt": sealed_at,
        "version": 1,
    }


def verify_seal(payload: dict, expected_hash: str) -> bool:
    """Verify that a payload matches its expected hash."""
    return compute_hash(payload) == expected_hash


def verify_chain(
    entries: List[Dict[str, Any]],
    hash_field: str = "chain_hash",
    prev_hash_field: str = "prev_chain_hash",
) -> bool:
    """Walk a hash chain and verify link integrity.

    Each entry must have ``hash_field`` matching the recomputed hash
    (with ``hash_field`` zeroed), and ``prev_hash_field`` matching the
    previous entry's ``hash_field``.
    """
    for i, entry in enumerate(entries):
        # Check prev link
        if i == 0:
            if entry.get(prev_hash_field) is not None:
                return False
        else:
            if entry.get(prev_hash_field) != entries[i - 1].get(hash_field):
                return False
        # Recompute hash
        hashable = dict(entry)
        hashable[hash_field] = ""
        expected = compute_hash(hashable)
        if entry.get(hash_field) != expected:
            return False
    return True
