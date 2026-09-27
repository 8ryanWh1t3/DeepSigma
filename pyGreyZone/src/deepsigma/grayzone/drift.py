"""Compare successive assessments without implying causal change."""

from __future__ import annotations

from .schema import Assessment


def compare(baseline: Assessment, current: Assessment) -> dict[str, object]:
    previous_events = {e.id for e in baseline.events}
    next_events = {e.id for e in current.events}
    previous_patterns = {frozenset(h.event_ids) for h in baseline.hypotheses}
    next_patterns = {frozenset(h.event_ids) for h in current.hypotheses}
    return {
        "baseline_id": baseline.id, "current_id": current.id,
        "new_events": sorted(next_events - previous_events),
        "no_longer_in_window": sorted(previous_events - next_events),
        "new_candidate_memberships": [sorted(x) for x in sorted(next_patterns - previous_patterns, key=lambda x: sorted(x))],
        "prior_candidate_memberships": [sorted(x) for x in sorted(previous_patterns - next_patterns, key=lambda x: sorted(x))],
        "note": "Membership changes may result from new data, source revisions, or window movement.",
    }
