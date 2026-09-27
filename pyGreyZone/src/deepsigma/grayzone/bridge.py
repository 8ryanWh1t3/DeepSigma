"""Dictionary adapters to the existing Deep Sigma core.cerpa model."""

from __future__ import annotations

from .cerpa import ReviewRecord
from .schema import Assessment, Event, Hypothesis


def core_event(event: Event) -> dict[str, object]:
    """Fields accepted by the attached repo's core.cerpa.models.Event."""
    return {
        "id": event.id, "text": event.summary or event.kind,
        "domain": "intelops", "source": event.sources[0].source_id,
        "timestamp": event.occurred_at.isoformat(),
        "observed_state": {"kind": event.kind, "channel": event.channel},
        "provenance": [{"source_id": s.source_id, "record_id": s.record_id,
                        "sha256": s.sha256, "lineage_group": s.independent_group,
                        "locator": s.locator}
                       for s in event.sources],
        "related_ids": list(event.entities + event.assets),
        "metadata": {"location": event.location, "tags": list(event.tags)},
    }


def core_claim(hypothesis: Hypothesis, assessment: Assessment) -> dict[str, object]:
    """Unreviewed Claim; do not run core's automatic cycle as an analytic verdict."""
    return {
        "id": hypothesis.id, "text": hypothesis.statement,
        "domain": "intelops", "source": "deepsigma.grayzone",
        "timestamp": assessment.window_end.isoformat() if assessment.window_end else "",
        "assumptions": list(hypothesis.collection_gaps),
        "related_ids": list(hypothesis.event_ids),
        "metadata": {"status": hypothesis.status, "priority_score": hypothesis.priority_score,
                     "assessment_id": assessment.id, "coordination_established": False},
    }


def core_review(review: ReviewRecord) -> dict[str, object]:
    """Human review mapped to a core.cerpa.models.Review compatible payload."""
    verdict = {"supported": "aligned", "not_supported": "mismatch",
               "inconclusive": "inconclusive"}[review.verdict]
    return {
        "id": review.id, "claim_id": review.claim_id,
        "event_id": review.event_ids[0], "domain": review.domain,
        "timestamp": review.reviewed_at.isoformat(), "verdict": verdict,
        "rationale": review.rationale, "drift_detected": review.verdict == "not_supported",
        "source": review.reviewer, "related_ids": list(review.event_ids),
        "metadata": {"grayzone_verdict": review.verdict,
                     "note": "Core verdict is an interop mapping, not an automated review."},
    }
