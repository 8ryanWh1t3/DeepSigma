"""Tests for core.cerpa.engine — CERPA cycle orchestration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cerpa.engine import (  # noqa: E402
    apply_patch,
    cycle_to_dict,
    generate_patch_from_review,
    review_claim_against_event,
    run_cerpa_cycle,
)
from core.cerpa.models import Claim, Event  # noqa: E402
from core.cerpa.types import CerpaDomain, CerpaStatus, ReviewVerdict  # noqa: E402


# ── Factories ────────────────────────────────────────────────────


def _aligned_claim() -> Claim:
    return Claim(
        id="claim-a1",
        text="Service uptime >= 99.9%",
        domain="reops",
        source="sla-monitor",
        timestamp="2026-03-01T10:00:00Z",
        assumptions=["Infrastructure is stable"],
    )


def _aligned_event() -> Event:
    return Event(
        id="event-a1",
        text="Service uptime is 99.95%",
        domain="reops",
        source="apm",
        timestamp="2026-03-02T10:00:00Z",
        observed_state={"status": "healthy", "uptime": 99.95},
    )


def _mismatch_claim() -> Claim:
    return Claim(
        id="claim-m1",
        text="Contractor delivers artifact by deadline",
        domain="actionops",
        source="contract-pm",
        timestamp="2026-03-01T09:00:00Z",
        assumptions=["Resources available"],
    )


def _mismatch_event() -> Event:
    return Event(
        id="event-m1",
        text="Artifact not delivered by deadline",
        domain="actionops",
        source="delivery-tracker",
        timestamp="2026-03-16T08:00:00Z",
        observed_state={"status": "failed", "artifact": "X"},
    )


def _violation_claim() -> Claim:
    return Claim(
        id="claim-v1",
        text="Agent must not emit restricted content",
        domain="authorityops",
        source="policy-001",
        timestamp="2026-03-01T08:00:00Z",
        assumptions=["Filter is active"],
    )


def _violation_event() -> Event:
    return Event(
        id="event-v1",
        text="Agent emitted restricted content",
        domain="authorityops",
        source="content-monitor",
        timestamp="2026-03-02T14:30:00Z",
        observed_state={"status": "violated"},
        metadata={"violation": True, "violation_detail": "Restricted content bypassed filter"},
    )


# ── Review tests ─────────────────────────────────────────────────


class TestReviewClaimAgainstEvent:
    def test_aligned(self) -> None:
        review = review_claim_against_event(_aligned_claim(), _aligned_event())
        assert review.verdict == ReviewVerdict.ALIGNED
        assert review.drift_detected is False
        assert review.severity is None

    def test_mismatch(self) -> None:
        review = review_claim_against_event(_mismatch_claim(), _mismatch_event())
        assert review.verdict == ReviewVerdict.MISMATCH
        assert review.drift_detected is True
        assert review.severity == "yellow"

    def test_violation(self) -> None:
        review = review_claim_against_event(_violation_claim(), _violation_event())
        assert review.verdict == ReviewVerdict.VIOLATION
        assert review.drift_detected is True
        assert review.severity == "red"

    def test_expired(self) -> None:
        claim = Claim(
            id="claim-e1",
            text="Data is fresh",
            domain="intelops",
            source="data-pipeline",
            timestamp="2026-01-01T00:00:00Z",
            metadata={"expired": True},
        )
        event = Event(
            id="event-e1",
            text="Data check",
            domain="intelops",
            source="scheduler",
            timestamp="2026-03-01T00:00:00Z",
        )
        review = review_claim_against_event(claim, event)
        assert review.verdict == ReviewVerdict.EXPIRED
        assert review.drift_detected is True

    def test_review_has_related_ids(self) -> None:
        review = review_claim_against_event(_aligned_claim(), _aligned_event())
        assert _aligned_claim().id in review.related_ids
        assert _aligned_event().id in review.related_ids


# ── Patch generation tests ───────────────────────────────────────


class TestGeneratePatch:
    def test_no_patch_when_aligned(self) -> None:
        review = review_claim_against_event(_aligned_claim(), _aligned_event())
        patch = generate_patch_from_review(review)
        assert patch is None

    def test_patch_on_mismatch(self) -> None:
        review = review_claim_against_event(_mismatch_claim(), _mismatch_event())
        patch = generate_patch_from_review(review)
        assert patch is not None
        assert patch.action == "adjust"
        assert patch.target == review.claim_id

    def test_patch_on_violation(self) -> None:
        review = review_claim_against_event(_violation_claim(), _violation_event())
        patch = generate_patch_from_review(review)
        assert patch is not None
        assert patch.action == "strengthen"


# ── Apply tests ──────────────────────────────────────────────────


class TestApplyPatch:
    def test_apply_success(self) -> None:
        review = review_claim_against_event(_mismatch_claim(), _mismatch_event())
        patch = generate_patch_from_review(review)
        assert patch is not None
        result = apply_patch(patch, _mismatch_claim())
        assert result.success is True
        assert _mismatch_claim().id in result.updated_claims
        assert result.new_state["action_taken"] == "adjust"


# ── Full cycle tests ─────────────────────────────────────────────


class TestRunCerpaCycle:
    def test_aligned_cycle(self) -> None:
        cycle = run_cerpa_cycle(_aligned_claim(), _aligned_event())
        assert cycle.status == CerpaStatus.ALIGNED
        assert cycle.patch is None
        assert cycle.apply_result is None
        assert cycle.review.drift_detected is False

    def test_mismatch_cycle(self) -> None:
        cycle = run_cerpa_cycle(_mismatch_claim(), _mismatch_event())
        assert cycle.status == CerpaStatus.APPLIED
        assert cycle.patch is not None
        assert cycle.apply_result is not None
        assert cycle.apply_result.success is True

    def test_violation_cycle(self) -> None:
        cycle = run_cerpa_cycle(_violation_claim(), _violation_event())
        assert cycle.status == CerpaStatus.APPLIED
        assert cycle.patch is not None
        assert cycle.patch.action == "strengthen"

    def test_cycle_has_timestamps(self) -> None:
        cycle = run_cerpa_cycle(_aligned_claim(), _aligned_event())
        assert cycle.started_at != ""
        assert cycle.completed_at != ""

    def test_all_domains_supported(self) -> None:
        for domain in CerpaDomain:
            claim = Claim(
                id=f"claim-{domain.value}",
                text="Test claim",
                domain=domain.value,
                source="test",
                timestamp="2026-03-01T00:00:00Z",
            )
            event = Event(
                id=f"event-{domain.value}",
                text="Test event",
                domain=domain.value,
                source="test",
                timestamp="2026-03-01T00:00:00Z",
            )
            cycle = run_cerpa_cycle(claim, event)
            assert cycle.domain == domain.value

    def test_cycle_to_dict(self) -> None:
        cycle = run_cerpa_cycle(_mismatch_claim(), _mismatch_event())
        d = cycle_to_dict(cycle)
        assert "cycle_id" in d
        assert "claim" in d
        assert "event" in d
        assert "review" in d
        assert "patch" in d
        assert "apply_result" in d
        assert d["status"] == "applied"
