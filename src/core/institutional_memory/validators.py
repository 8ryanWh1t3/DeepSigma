"""Validation functions for institutional memory objects."""

from __future__ import annotations

from typing import Any, Dict, List


VALID_CATEGORIES = frozenset({
    "degrade_pattern",
    "drift_recurrence",
    "outcome_anomaly",
})


def validate_precedent(data: Dict[str, Any]) -> List[str]:
    """Validate precedent input data. Returns list of error strings."""
    errors: List[str] = []
    if not data.get("takeaway"):
        errors.append("takeaway is required")
    if not data.get("sourceSessionId") and not data.get("source_session_id"):
        errors.append("sourceSessionId is required")
    category = data.get("category", "")
    if category and category not in VALID_CATEGORIES:
        errors.append(f"category must be one of {sorted(VALID_CATEGORIES)}")
    confidence = data.get("confidence", 0)
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        errors.append("confidence must be a number in [0, 1]")
    return errors


def validate_knowledge_entry(data: Dict[str, Any]) -> List[str]:
    """Validate knowledge entry input data. Returns list of error strings."""
    errors: List[str] = []
    if not data.get("title"):
        errors.append("title is required")
    if not data.get("summary"):
        errors.append("summary is required")
    return errors
