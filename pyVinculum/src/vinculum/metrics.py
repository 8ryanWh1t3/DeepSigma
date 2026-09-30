from __future__ import annotations

from math import log2
from typing import Iterable

from .governance import GovernanceStatus
from .models import BindingResult, BoundedState


def normalized_entropy(probabilities: Iterable[float]) -> float:
    vals = [max(0.0, float(p)) for p in probabilities]
    total = sum(vals)
    if total <= 0 or len(vals) <= 1:
        return 0.0
    ps = [p / total for p in vals if p > 0]
    entropy = -sum(p * log2(p) for p in ps)
    max_entropy = log2(len(vals))
    return entropy / max_entropy if max_entropy else 0.0


def report_metrics(results: Iterable[BindingResult]) -> dict[str, float]:
    rows = list(results)
    if not rows:
        return {
            "candidate_count": 0.0,
            "accepted_count": 0.0,
            "rejected_count": 0.0,
            "unresolved_count": 0.0,
            "mean_constraint_coverage": 0.0,
            "mean_governance_coverage": 0.0,
            "governance_pass_count": 0.0,
            "governance_fail_count": 0.0,
            "governance_unknown_count": 0.0,
            "candidate_entropy": 0.0,
        }

    return {
        "candidate_count": float(len(rows)),
        "accepted_count": float(sum(r.state is BoundedState.ACCEPTED for r in rows)),
        "rejected_count": float(sum(r.state is BoundedState.REJECTED for r in rows)),
        "unresolved_count": float(sum(r.state is BoundedState.UNRESOLVED for r in rows)),
        "mean_constraint_coverage": sum(r.constraint_coverage for r in rows) / len(rows),
        "mean_governance_coverage": sum(r.governance_coverage for r in rows) / len(rows),
        "governance_pass_count": float(sum(r.governance_status is GovernanceStatus.PASS for r in rows)),
        "governance_fail_count": float(sum(r.governance_status is GovernanceStatus.FAIL for r in rows)),
        "governance_unknown_count": float(sum(r.governance_status is GovernanceStatus.UNKNOWN for r in rows)),
        "candidate_entropy": normalized_entropy(r.hypothesis.probability for r in rows),
    }
