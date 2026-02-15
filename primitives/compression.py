from __future__ import annotations

import hashlib
import json
from typing import Any


def _stable_claim_repr(claim: Any) -> str:
    """Render a claim into a stable string representation."""
    if isinstance(claim, (dict, list)):
        return json.dumps(claim, sort_keys=True)
    return str(claim)


def calculate_entropy(claims: list[Any]) -> float:
    """Compute a simple uniqueness ratio for claims."""
    if not claims:
        return 0.0

    values = [_stable_claim_repr(c) for c in claims]
    return len(set(values)) / len(values)


def compress_claims(claims: list[Any]) -> dict[str, float | int]:
    """Compress claims into a hash + summary statistics."""
    serialized = "".join(sorted(_stable_claim_repr(c) for c in claims))
    digest = hashlib.sha256(serialized.encode("utf-8")).digest()
    semantic_hash = int.from_bytes(digest[:8], "big")

    return {
        "claim_count": len(claims),
        "semantic_hash": semantic_hash,
        "entropy": calculate_entropy(claims),
    }
