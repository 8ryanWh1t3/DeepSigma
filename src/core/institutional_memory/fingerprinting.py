"""Pattern fingerprinting for institutional memory.

Computes structural fingerprints from episodes and precedents,
and provides similarity scoring between fingerprints.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .models import PatternFingerprint


def compute_fingerprint(
    precedent_id: str,
    episodes: List[Dict[str, Any]],
) -> PatternFingerprint:
    """Compute a structural fingerprint from a set of episodes.

    Extracts outcome distribution, drift signature, and degrade frequency
    to create a searchable pattern vector.
    """
    outcome_vector: Dict[str, float] = {}
    drift_signature: Dict[str, int] = {}
    degrade_count = 0
    total = len(episodes) or 1

    for ep in episodes:
        # Outcome distribution
        outcome = ep.get("outcome_code", ep.get("outcome", "unknown"))
        outcome_vector[outcome] = outcome_vector.get(outcome, 0) + 1

        # Drift signature
        for drift in ep.get("drift_signals", []):
            dtype = drift.get("driftType", drift.get("drift_type", "unknown"))
            drift_signature[dtype] = drift_signature.get(dtype, 0) + 1

        # Degrade tracking
        if ep.get("degrade_step") or ep.get("degradeStep"):
            degrade_count += 1

    # Normalize outcome vector to proportions
    for k in outcome_vector:
        outcome_vector[k] = round(outcome_vector[k] / total, 4)

    fingerprint_id = f"FP-{uuid.uuid4().hex[:8]}"
    return PatternFingerprint(
        fingerprint_id=fingerprint_id,
        precedent_id=precedent_id,
        outcome_vector=outcome_vector,
        drift_signature=drift_signature,
        degrade_frequency=round(degrade_count / total, 4),
        episode_count=len(episodes),
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def similarity_score(a: PatternFingerprint, b: PatternFingerprint) -> float:
    """Compute similarity between two fingerprints.

    Uses cosine-like overlap of outcome vectors and drift signatures.
    Returns a float in [0.0, 1.0].
    """
    # Outcome vector similarity (Jaccard-like)
    all_outcomes = set(a.outcome_vector) | set(b.outcome_vector)
    if not all_outcomes:
        outcome_sim = 0.0
    else:
        intersection = sum(
            min(a.outcome_vector.get(k, 0), b.outcome_vector.get(k, 0))
            for k in all_outcomes
        )
        union = sum(
            max(a.outcome_vector.get(k, 0), b.outcome_vector.get(k, 0))
            for k in all_outcomes
        )
        outcome_sim = intersection / union if union > 0 else 0.0

    # Drift signature similarity
    all_drifts = set(a.drift_signature) | set(b.drift_signature)
    if not all_drifts:
        drift_sim = 0.0
    else:
        d_intersection = sum(
            min(a.drift_signature.get(k, 0), b.drift_signature.get(k, 0))
            for k in all_drifts
        )
        d_union = sum(
            max(a.drift_signature.get(k, 0), b.drift_signature.get(k, 0))
            for k in all_drifts
        )
        drift_sim = d_intersection / d_union if d_union > 0 else 0.0

    # Weighted combination
    return round(0.6 * outcome_sim + 0.4 * drift_sim, 4)
