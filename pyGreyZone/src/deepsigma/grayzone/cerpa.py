"""Human-authored CERPA records; proposals cannot execute an operational action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .provenance import digest
from .schema import Assessment, parse_time


@dataclass(frozen=True)
class ReviewRecord:
    id: str
    claim_id: str
    event_ids: tuple[str, ...]
    reviewer: str
    verdict: str
    rationale: str
    reviewed_at: datetime
    domain: str = "intelops"


@dataclass(frozen=True)
class PatchProposal:
    id: str
    review_id: str
    proposer: str
    action: str
    description: str
    status: str = "proposed"
    approved_by: str = ""
    approved_at: datetime | None = None


@dataclass(frozen=True)
class ApplyRecord:
    id: str
    patch_id: str
    approver: str
    applied_at: datetime
    outcome: str
    note: str


def review_hypothesis(assessment: Assessment, claim_id: str, *, reviewer: str,
                      verdict: str, rationale: str, reviewed_at: str | datetime) -> ReviewRecord:
    if verdict not in {"supported", "not_supported", "inconclusive"}:
        raise ValueError("verdict must be supported, not_supported, or inconclusive")
    if not reviewer.strip() or not rationale.strip():
        raise ValueError("reviewer and rationale are required")
    hypothesis = next((h for h in assessment.hypotheses if h.id == claim_id), None)
    if hypothesis is None:
        raise ValueError("claim_id must reference a hypothesis in this assessment")
    stamp = parse_time(reviewed_at)
    key = (assessment.id, claim_id, reviewer, verdict, rationale, stamp.isoformat())
    return ReviewRecord("review-" + digest(key)[:12], claim_id, hypothesis.event_ids,
                        reviewer, verdict, rationale, stamp)


def propose_patch(review: ReviewRecord, *, proposer: str, action: str,
                  description: str) -> PatchProposal:
    if not proposer.strip() or not action.strip() or not description.strip():
        raise ValueError("proposer, action and description are required")
    key = (review.id, proposer, action, description)
    return PatchProposal("patch-" + digest(key)[:12], review.id, proposer, action, description)


def approve_patch(patch: PatchProposal, *, approver: str,
                  approved_at: str | datetime) -> PatchProposal:
    from dataclasses import replace
    if patch.status != "proposed" or not approver.strip():
        raise ValueError("proposed patch and named approver required")
    return replace(patch, status="approved", approved_by=approver,
                   approved_at=parse_time(approved_at))


def record_apply(patch: PatchProposal, *, approver: str, applied_at: str | datetime,
                 outcome: str, note: str) -> ApplyRecord:
    if not approver.strip() or not outcome.strip() or not note.strip():
        raise ValueError("approver, outcome and note are required")
    if patch.status != "approved" or not patch.approved_by or patch.approved_at is None:
        raise ValueError("patch requires a recorded approval before application")
    stamp = parse_time(applied_at)
    return ApplyRecord("apply-" + digest((patch.id, approver, stamp.isoformat(), outcome, note))[:12],
                       patch.id, approver, stamp, outcome, note)


def cerpa_packet(assessment: Assessment, review: ReviewRecord | None = None,
                 patch: PatchProposal | None = None,
                 apply: ApplyRecord | None = None) -> dict[str, object]:
    from dataclasses import asdict
    if review and review.claim_id not in {h.id for h in assessment.hypotheses}:
        raise ValueError("review is not for this assessment")
    if patch and (not review or patch.review_id != review.id):
        raise ValueError("patch does not reference this review")
    if apply and (not patch or apply.patch_id != patch.id):
        raise ValueError("apply record does not reference this patch")
    def serializable(value: object) -> object:
        if value is None:
            return None
        record = asdict(value)
        for key, item in record.items():
            if isinstance(item, datetime):
                record[key] = item.isoformat()
        return record

    return {"claim": [{"id": h.id, "text": h.statement, "status": h.status} for h in assessment.hypotheses],
            "event": [e.id for e in assessment.events],
            "review": serializable(review),
            "patch": serializable(patch),
            "apply": serializable(apply)}
