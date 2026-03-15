"""COG artifact heuristic mapping — suggest CERPA stages for unmapped refTypes.

When an artifact has an unrecognised ref_type, this module inspects payload
keys to suggest the most likely COG refType and corresponding CERPA stage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .models import CogMappingSuggestion

# Signal groups: (payload_keys, suggested_ref_type, cerpa_stage, weight)
_SIGNAL_TABLE: List[Tuple[frozenset, str, str, float]] = [
    # Patch-like artifacts → Apply stage
    (
        frozenset({"patchId", "action", "supersedes", "target", "correction"}),
        "patch",
        "Apply",
        0.25,
    ),
    # Drift-like artifacts → Review stage
    (
        frozenset({"severity", "trigger", "observed_state", "expected_state", "drift"}),
        "drift",
        "Review",
        0.25,
    ),
    # Memory-like artifacts → Apply stage (precedent recall)
    (
        frozenset({"precedentId", "recall", "takeaway", "retention", "context_snapshot"}),
        "memory",
        "Apply",
        0.25,
    ),
    # Rationale-like artifacts → Review stage
    (
        frozenset({"decisionId", "rationale", "selectedOption", "alternatives", "justification"}),
        "rationale",
        "Review",
        0.25,
    ),
]

_DEFAULT_REF_TYPE = "evidence"
_DEFAULT_STAGE = "Claim"


def suggest_cerpa_stage(
    payload: Dict[str, Any],
    ref_type: str,
) -> CogMappingSuggestion:
    """Inspect *payload* keys and suggest a CERPA stage for an unmapped *ref_type*.

    Returns a ``CogMappingSuggestion`` with confidence in [0.0, 1.0].
    Higher confidence means more payload keys matched a known signal group.
    """
    payload_keys = set(payload.keys()) if payload else set()

    best_type = _DEFAULT_REF_TYPE
    best_stage = _DEFAULT_STAGE
    best_score: float = 0.0
    best_signals: List[str] = []

    for signal_keys, suggested_type, stage, weight in _SIGNAL_TABLE:
        matched = payload_keys & signal_keys
        if not matched:
            continue
        score = len(matched) * weight
        if score > best_score:
            best_score = score
            best_type = suggested_type
            best_stage = stage
            best_signals = sorted(matched)

    confidence = min(best_score, 1.0)

    return CogMappingSuggestion(
        original_ref_type=ref_type,
        suggested_ref_type=best_type,
        suggested_cerpa_stage=best_stage,
        confidence=confidence,
        signals=best_signals,
    )
