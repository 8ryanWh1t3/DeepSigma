"""Consensus scoring — measure agreement across adapter results."""

from __future__ import annotations

import re
import string
from typing import List, Set

from .models import ReasoningResult


def _normalise_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _token_set(text: str) -> Set[str]:
    return set(_normalise_text(text).split())


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def claim_overlap_score(results: List[ReasoningResult]) -> float:
    """Pairwise Jaccard overlap of claim texts across results."""
    if len(results) < 2:
        return 1.0
    claim_sets = [
        {_normalise_text(c.text) for c in r.claims} for r in results
    ]
    pairs = 0
    total = 0.0
    for i in range(len(claim_sets)):
        for j in range(i + 1, len(claim_sets)):
            total += _jaccard(claim_sets[i], claim_sets[j])
            pairs += 1
    return total / pairs if pairs else 1.0


def reasoning_overlap_score(results: List[ReasoningResult]) -> float:
    """Token-level Jaccard overlap of reasoning step texts."""
    if len(results) < 2:
        return 1.0
    token_sets = [
        set().union(*(_token_set(s.text) for s in r.reasoning)) if r.reasoning else set()
        for r in results
    ]
    pairs = 0
    total = 0.0
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            total += _jaccard(token_sets[i], token_sets[j])
            pairs += 1
    return total / pairs if pairs else 1.0


def agreement_score(results: List[ReasoningResult]) -> float:
    """Weighted average of claim overlap (0.6) and reasoning overlap (0.4)."""
    co = claim_overlap_score(results)
    ro = reasoning_overlap_score(results)
    return 0.6 * co + 0.4 * ro
