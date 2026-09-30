from __future__ import annotations

from typing import Any


def automation_candidates(work: list[Any], min_volume: float = 20.0) -> list[dict]:
    """Score work architecture, never people.

    This is a triage score for where to inspect automation potential. It is not an authority to automate.
    """
    out = []
    for w in work:
        if not w.active or w.mission_critical:
            continue
        # Do not automate work that has not first been justified by mission and policy.
        # Orphan work must be validated/eliminated before automation is considered.
        if not w.mission_id or not w.policy_ids:
            continue
        score = 0
        reasons = []
        if w.volume_per_month >= min_volume:
            score += 2
            reasons.append("high recurring volume")
        if w.rule_defined:
            score += 3
            reasons.append("rule-defined steps")
        if w.touch_time_hours <= 2.0:
            score += 1
            reasons.append("bounded touch time")
        if w.approval_steps <= 1:
            score += 1
            reasons.append("few approval gates")
        if w.rework_rate >= 0.10:
            score += 1
            reasons.append("rework suggests standardization opportunity")
        if score >= 4:
            out.append({
                "type": "AUTOMATION_CANDIDATE",
                "work_id": w.id,
                "score": score,
                "reasons": reasons,
                "guardrail": "Validate policy, authority, exceptions, and human decision rights before automation.",
            })
    return sorted(out, key=lambda x: x["score"], reverse=True)
