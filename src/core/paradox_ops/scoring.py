"""Pressure scoring and imbalance computation for Paradox Tension Sets.

Pressure measures how much competing truths are colliding in the same
operational space. Imbalance vectors show directional skew across poles.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ParadoxTensionSet, TensionDimension, TensionPole


# ── Pressure components ──────────────────────────────────────────

def _pole_dispersion(poles: List[TensionPole]) -> float:
    """Variance of pole weights, normalized to 0-1.

    Equal weights → 0.0, extreme skew → approaches 1.0.
    """
    if len(poles) < 2:
        return 0.0
    weights = [p.weight for p in poles]
    mean = sum(weights) / len(weights)
    variance = sum((w - mean) ** 2 for w in weights) / len(weights)
    max_var = mean ** 2
    if max_var == 0:
        return 0.0
    return min(1.0, variance / max_var)


def _dimension_strain(dimensions: List[TensionDimension]) -> float:
    """Max absolute shift across all dimensions, normalized to 0-1."""
    if not dimensions:
        return 0.0
    shifts = [abs(d.current_value - d.previous_value) for d in dimensions]
    return min(1.0, max(shifts))


def _threshold_proximity(dimensions: List[TensionDimension]) -> float:
    """How close the most-shifted dimension is to its threshold.

    Returns 1.0 when a dimension is at or beyond its threshold,
    0.0 when all dimensions are far from their thresholds.
    """
    if not dimensions:
        return 0.0
    proximities: List[float] = []
    for d in dimensions:
        shift = abs(d.current_value - d.previous_value)
        if d.threshold <= 0:
            proximities.append(1.0 if shift > 0 else 0.0)
        else:
            proximities.append(min(1.0, shift / d.threshold))
    return max(proximities)


def _rate_of_change(dimensions: List[TensionDimension]) -> float:
    """Fraction of dimensions that have shifted (have a shifted_at timestamp)."""
    if not dimensions:
        return 0.0
    shifted_count = sum(1 for d in dimensions if d.shifted_at is not None)
    return shifted_count / len(dimensions)


# ── Public API ───────────────────────────────────────────────────

def compute_pressure(
    pts: ParadoxTensionSet,
    context: Optional[Dict[str, Any]] = None,
) -> float:
    """Compute pressure score 0.0-1.0 from weighted components.

    Components (weights):
        pole_dispersion:    0.3
        dimension_strain:   0.3
        threshold_proximity: 0.2
        rate_of_change:     0.2
    """
    pd = _pole_dispersion(pts.poles)
    ds = _dimension_strain(pts.dimensions)
    tp = _threshold_proximity(pts.dimensions)
    rc = _rate_of_change(pts.dimensions)

    score = (pd * 0.3) + (ds * 0.3) + (tp * 0.2) + (rc * 0.2)
    return round(min(1.0, max(0.0, score)), 3)


def compute_imbalance(pts: ParadoxTensionSet) -> List[float]:
    """Compute imbalance vector based on pole count.

    - Pair (2): single value in [-1.0, +1.0]
    - Triple (3): 3-value vector summing to ~0
    - 4+ poles: n-value vector, each = w_i/sum - 1/n
    """
    poles = pts.poles
    n = len(poles)
    if n < 2:
        return [0.0]

    weights = [p.weight for p in poles]
    total = sum(weights)
    if total == 0:
        return [0.0] * n

    if n == 2:
        ratio = weights[0] / total
        return [round((ratio - 0.5) * 2, 4)]

    even_share = 1.0 / n
    return [round(w / total - even_share, 4) for w in weights]


def evaluate_thresholds(pts: ParadoxTensionSet) -> List[Dict[str, Any]]:
    """Evaluate all dimensions against their thresholds.

    Returns a list of breach dicts for dimensions where the shift
    exceeds the threshold.
    """
    breaches: List[Dict[str, Any]] = []
    for d in pts.dimensions:
        shift = abs(d.current_value - d.previous_value)
        if shift > d.threshold:
            breaches.append({
                "dimensionId": d.dimension_id,
                "dimensionName": d.name,
                "shift": round(shift, 4),
                "threshold": d.threshold,
                "isGovernanceRelevant": d.is_governance_relevant,
            })
    return breaches
