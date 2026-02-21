#!/usr/bin/env python3
"""Deterministic Merkle tree primitives for selective disclosure.

Builds a binary Merkle tree over an ordered list of leaf hashes.
Leaf order is caller-determined (typically lexicographic by label).
Odd-count leaf sets are padded by duplicating the last leaf.

Internal node hash: sha256_text(left + "|" + right)
"""
from __future__ import annotations

from canonical_json import sha256_text

EMPTY_ROOT = sha256_text("empty-merkle")


def merkle_root(leaf_hashes: list[str]) -> str:
    """Compute the Merkle root of an ordered list of sha256 hashes.

    Returns sha256:... string.  Empty list returns EMPTY_ROOT.
    """
    if not leaf_hashes:
        return EMPTY_ROOT

    level = list(leaf_hashes)

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate last for odd count

        next_level: list[str] = []
        for i in range(0, len(level), 2):
            combined = sha256_text(level[i] + "|" + level[i + 1])
            next_level.append(combined)
        level = next_level

    return level[0]


def verify_merkle_root(leaf_hashes: list[str], expected_root: str) -> bool:
    """Recompute the Merkle root and compare against expected."""
    return merkle_root(leaf_hashes) == expected_root
