"""Contradiction detection — conservative heuristic-based checks."""

from __future__ import annotations

import re
import string
import uuid
from typing import List

from .models import CandidateClaim, ContradictionRecord, ReasoningResult

_NEGATION_WORDS = frozenset({
    "no", "not", "never", "none", "nothing", "neither", "nobody",
    "cannot", "cant", "isnt", "arent", "doesnt", "dont", "wont",
    "shouldnt", "wouldnt", "couldnt", "without", "impossible",
    "unlikely", "false", "incorrect", "wrong", "invalid",
})

_POLARITY_POSITIVE = frozenset({
    "safe", "secure", "compliant", "valid", "healthy", "stable",
    "approved", "allowed", "acceptable", "correct", "pass",
})

_POLARITY_NEGATIVE = frozenset({
    "unsafe", "insecure", "noncompliant", "invalid", "unhealthy",
    "unstable", "rejected", "blocked", "unacceptable", "incorrect",
    "fail", "failure", "violation",
})


def _normalise(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> set:
    return set(_normalise(text).split())


def _has_negation_conflict(tokens_a: set, tokens_b: set) -> bool:
    """True if one side has strong negation overlap with the other."""
    neg_a = tokens_a & _NEGATION_WORDS
    neg_b = tokens_b & _NEGATION_WORDS
    if bool(neg_a) != bool(neg_b):
        shared_content = (tokens_a - _NEGATION_WORDS) & (tokens_b - _NEGATION_WORDS)
        if len(shared_content) >= 2:
            return True
    return False


def _has_polarity_mismatch(tokens_a: set, tokens_b: set) -> bool:
    """True if claims use opposite polarity terms."""
    pos_a = tokens_a & _POLARITY_POSITIVE
    neg_a = tokens_a & _POLARITY_NEGATIVE
    pos_b = tokens_b & _POLARITY_POSITIVE
    neg_b = tokens_b & _POLARITY_NEGATIVE
    if (pos_a and neg_b) or (neg_a and pos_b):
        return True
    return False


def _assess_severity(tokens_a: set, tokens_b: set) -> str:
    """Assign severity based on the strength of the contradiction signal."""
    neg_a = tokens_a & _NEGATION_WORDS
    neg_b = tokens_b & _NEGATION_WORDS
    pol_mismatch = _has_polarity_mismatch(tokens_a, tokens_b)
    if pol_mismatch and (neg_a or neg_b):
        return "high"
    if pol_mismatch or (neg_a and neg_b):
        return "medium"
    return "low"


def detect_claim_contradictions(
    results: List[ReasoningResult],
) -> List[ContradictionRecord]:
    """Detect contradictions across claims from multiple adapter results."""
    all_claims: List[tuple] = []
    for r in results:
        for c in r.claims:
            all_claims.append((r.adapter_name, c))

    records: List[ContradictionRecord] = []
    for i in range(len(all_claims)):
        for j in range(i + 1, len(all_claims)):
            name_a, claim_a = all_claims[i]
            name_b, claim_b = all_claims[j]
            if name_a == name_b:
                continue
            tok_a = _tokens(claim_a.text)
            tok_b = _tokens(claim_b.text)
            if _has_negation_conflict(tok_a, tok_b) or _has_polarity_mismatch(
                tok_a, tok_b
            ):
                records.append(
                    ContradictionRecord(
                        contradiction_id=f"CTR-{uuid.uuid4().hex[:8]}",
                        severity=_assess_severity(tok_a, tok_b),
                        left_ref=claim_a.claim_id,
                        right_ref=claim_b.claim_id,
                        note=(
                            f"Potential contradiction between "
                            f"'{claim_a.text[:60]}' ({name_a}) and "
                            f"'{claim_b.text[:60]}' ({name_b})"
                        ),
                    )
                )
    return records


def contradiction_score(results: List[ReasoningResult]) -> float:
    """Return a normalised contradiction score in [0.0, 1.0].

    Higher means more contradictions detected.
    """
    records = detect_claim_contradictions(results)
    if not records:
        return 0.0
    total_claims = sum(len(r.claims) for r in results)
    if total_claims < 2:
        return 0.0
    max_pairs = total_claims * (total_claims - 1) / 2
    return min(1.0, len(records) / max_pairs)
