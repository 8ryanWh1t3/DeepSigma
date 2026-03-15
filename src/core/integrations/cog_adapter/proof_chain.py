"""COG proof chain — per-artifact hash chain build and verify.

Follows the hash chain pattern from ``core.authority.seal_and_hash`` and
``core.authority.evidence_chain``: each entry carries a ``chain_hash``
computed over its own fields (with the hash field zeroed), and a
``prev_chain_hash`` linking it to the previous entry.

Functions:
    build_proof_chain   — create per-artifact chain entries
    verify_proof_chain  — walk chain and verify link integrity
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.authority.seal_and_hash import compute_hash

from .models import CogArtifactRef


def build_proof_chain(artifacts: List[CogArtifactRef]) -> List[Dict[str, Any]]:
    """Build a per-artifact proof chain.

    Each entry contains:
        index          — position in the chain
        ref_id         — artifact ref ID
        content_hash   — artifact content hash
        type           — "artifact_link"
        chain_hash     — hash of this entry (with chain_hash zeroed)
        prev_chain_hash — previous entry's chain_hash (None for first)

    Returns the chain as a list of dicts.
    """
    chain: List[Dict[str, Any]] = []
    prev_hash = None

    for i, artifact in enumerate(artifacts):
        entry: Dict[str, Any] = {
            "index": i,
            "refId": artifact.ref_id,
            "contentHash": artifact.content_hash,
            "type": "artifact_link",
            "chainHash": "",
            "prevChainHash": prev_hash,
        }
        # Compute chain hash over all fields with chainHash zeroed
        entry["chainHash"] = compute_hash(entry)
        prev_hash = entry["chainHash"]
        chain.append(entry)

    return chain


def verify_proof_chain(chain: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Walk a proof chain and verify link integrity.

    Returns (valid, errors) where errors is a list of human-readable
    error messages. An empty chain is considered valid.
    """
    if not chain:
        return True, []

    errors: List[str] = []

    for i, entry in enumerate(chain):
        # Check prev link
        if i == 0:
            if entry.get("prevChainHash") is not None:
                errors.append(
                    f"chain[0]: prevChainHash should be null, "
                    f"got {entry.get('prevChainHash')}"
                )
        else:
            expected_prev = chain[i - 1].get("chainHash")
            if entry.get("prevChainHash") != expected_prev:
                errors.append(
                    f"chain[{i}]: prevChainHash mismatch: "
                    f"expected {expected_prev}, got {entry.get('prevChainHash')}"
                )

        # Recompute hash
        hashable = dict(entry)
        hashable["chainHash"] = ""
        expected_hash = compute_hash(hashable)
        if entry.get("chainHash") != expected_hash:
            errors.append(
                f"chain[{i}]: chainHash mismatch: "
                f"expected {expected_hash}, got {entry.get('chainHash')}"
            )

    return len(errors) == 0, errors
