from __future__ import annotations

import re
from typing import Iterable, Set

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]+")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
}


def tokens(text: str) -> Set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP}


def feature_terms(text: str, tags: Iterable[str] = ()) -> Set[str]:
    out = tokens(text)
    for tag in tags:
        out |= tokens(tag)
    return out


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)
