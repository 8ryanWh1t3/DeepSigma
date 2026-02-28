"""Centralized severity scoring for drift signals and episodes.

All domains call this module for consistent severity classification.
Scoring uses drift type weights and severity mappings.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Severity levels ordered by priority (highest first)
SEVERITY_ORDER = {"red": 3, "yellow": 2, "green": 1}

# Base severity scores per drift type
DRIFT_TYPE_WEIGHTS: Dict[str, float] = {
    "authority_mismatch": 0.9,
    "freshness": 0.6,
    "process_gap": 0.5,
    "confidence_decay": 0.4,
    "canon_inflation": 0.5,
    "time": 0.3,
    "fallback": 0.4,
    "verify": 0.7,
    "outcome": 0.6,
}


def compute_severity_score(
    drift_type: str,
    severity: str,
    context: Optional[Dict[str, Any]] = None,
) -> float:
    """Compute a 0.0-1.0 severity score from drift type and severity level.

    Args:
        drift_type: The type of drift signal.
        severity: The severity level (red/yellow/green).
        context: Optional additional context (e.g., recurrence count).

    Returns:
        A float severity score between 0.0 and 1.0.
    """
    base = DRIFT_TYPE_WEIGHTS.get(drift_type, 0.5)
    severity_multiplier = {
        "red": 1.0,
        "yellow": 0.6,
        "green": 0.2,
    }.get(severity, 0.5)

    score = base * severity_multiplier

    # Boost for recurrence
    ctx = context or {}
    recurrence = ctx.get("recurrence_count", 0)
    if recurrence > 0:
        score = min(1.0, score + (recurrence * 0.05))

    return round(min(1.0, max(0.0, score)), 3)


def classify_severity(score: float) -> str:
    """Classify a severity score into red/yellow/green."""
    if score >= 0.7:
        return "red"
    elif score >= 0.3:
        return "yellow"
    return "green"


def aggregate_severity(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multiple drift signals into a single severity assessment.

    Returns a dict with overall severity, max score, signal count, and breakdown.
    """
    if not signals:
        return {
            "overall": "green",
            "maxScore": 0.0,
            "signalCount": 0,
            "breakdown": {},
        }

    scores: List[float] = []
    by_type: Dict[str, int] = {}

    for sig in signals:
        dt = sig.get("driftType", "process_gap")
        sev = sig.get("severity", "yellow")
        s = compute_severity_score(dt, sev)
        scores.append(s)
        by_type[dt] = by_type.get(dt, 0) + 1

    max_score = max(scores)
    return {
        "overall": classify_severity(max_score),
        "maxScore": max_score,
        "signalCount": len(signals),
        "breakdown": by_type,
    }
