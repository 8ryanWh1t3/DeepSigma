from __future__ import annotations

from datetime import datetime
from typing import Optional


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def altcog_discovery_rate(credible_candidates: int, major_decision_streams: int) -> float:
    """ADR = CredibleAltCogCandidates / MajorDecisionStreams."""
    return _ratio(credible_candidates, major_decision_streams)


def residual_conversion_rate(residuals_converted_to_tests: int, significant_residuals: int) -> float:
    """RCR = ResidualsConvertedToTests / SignificantResiduals."""
    return _ratio(residuals_converted_to_tests, significant_residuals)


def weak_signal_promotion_rate(weak_signals_promoted: int, weak_signals_reviewed: int) -> float:
    """WPR = WeakSignalsPromoted / WeakSignalsReviewed."""
    return _ratio(weak_signals_promoted, weak_signals_reviewed)


def time_to_alternative_formation(first_signal_detected_at: str, candidate_created_at: str) -> float:
    """TAF in seconds = CandidateModelCreatedAt − FirstSignalDetectedAt."""
    first = datetime.fromisoformat(first_signal_detected_at.replace("Z", "+00:00"))
    created = datetime.fromisoformat(candidate_created_at.replace("Z", "+00:00"))
    return max(0.0, (created - first).total_seconds())


def dormant_alternative_recall(reactivated_preserved_alternatives: int, relevant_reality_changes: int) -> float:
    """DAR = ReactivatedPreservedAlternatives / RelevantRealityChanges."""
    return _ratio(reactivated_preserved_alternatives, relevant_reality_changes)
