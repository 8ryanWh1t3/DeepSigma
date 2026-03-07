"""Tests for core.cerpa.mappers — bidirectional adapters."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cerpa.mappers import (  # noqa: E402
    claim_from_atomic,
    claim_to_atomic,
    event_from_surface,
    patch_from_canonical,
    patch_to_canonical,
    review_from_drift,
    review_from_dlr,
)
from core.primitives import (  # noqa: E402
    AtomicClaim,
    DriftSignal,
    Patch as CanonicalPatch,
)


# ── AtomicClaim <-> CERPA Claim ─────────────────────────────────


class TestClaimMappers:
    def test_claim_from_atomic(self) -> None:
        atomic = AtomicClaim(
            claim_id="CLAIM-2026-0001",
            claim_type="observation",
            statement="Latency p99 under 200ms",
            source="apm-monitor",
            confidence=0.92,
            created_at="2026-03-01T10:00:00Z",
            provenance=[{"type": "source", "ref": "apm-001", "role": "primary"}],
            tags=["latency"],
        )
        cerpa_claim = claim_from_atomic(atomic, domain="reops")
        assert cerpa_claim.id == "CLAIM-2026-0001"
        assert cerpa_claim.text == "Latency p99 under 200ms"
        assert cerpa_claim.domain == "reops"
        assert cerpa_claim.source == "apm-monitor"
        assert cerpa_claim.timestamp == "2026-03-01T10:00:00Z"
        assert cerpa_claim.metadata["confidence"] == 0.92
        assert cerpa_claim.metadata["claim_type"] == "observation"
        assert cerpa_claim.provenance == [{"type": "source", "ref": "apm-001", "role": "primary"}]

    def test_claim_to_atomic(self) -> None:
        from core.cerpa.models import Claim

        cerpa_claim = Claim(
            id="CLAIM-2026-0002",
            text="Service is healthy and responding",
            domain="intelops",
            source="health-check",
            timestamp="2026-03-01T12:00:00Z",
            metadata={"claim_type": "observation", "confidence": 0.85, "tags": ["health"]},
        )
        atomic = claim_to_atomic(cerpa_claim)
        assert atomic.claim_id == "CLAIM-2026-0002"
        assert atomic.statement == "Service is healthy and responding"
        assert atomic.claim_type == "observation"
        assert atomic.confidence == 0.85
        assert atomic.tags == ["health"]

    def test_round_trip_preserves_core_fields(self) -> None:
        atomic = AtomicClaim(
            claim_id="CLAIM-2026-0003",
            claim_type="inference",
            statement="Traffic will increase during peak hours",
            source="traffic-model",
            confidence=0.75,
            created_at="2026-03-01T08:00:00Z",
        )
        cerpa_claim = claim_from_atomic(atomic, domain="intelops")
        roundtripped = claim_to_atomic(cerpa_claim)
        assert roundtripped.claim_id == atomic.claim_id
        assert roundtripped.statement == atomic.statement
        assert roundtripped.source == atomic.source
        assert roundtripped.claim_type == atomic.claim_type
        assert roundtripped.confidence == atomic.confidence


# ── decision_surface.Event -> CERPA Event ───────────────────────


class TestEventMapper:
    def test_event_from_surface(self) -> None:
        from core.decision_surface.models import Event as SurfaceEvent

        surface = SurfaceEvent(
            event_id="evt-001",
            event_type="latency_spike",
            source="apm",
            payload={"p99": 280},
            timestamp="2026-03-02T10:00:00Z",
            claim_refs=["CLAIM-2026-0001"],
        )
        cerpa_event = event_from_surface(surface, domain="reops")
        assert cerpa_event.id == "evt-001"
        assert cerpa_event.domain == "reops"
        assert cerpa_event.source == "apm"
        assert cerpa_event.observed_state == {"p99": 280}
        assert cerpa_event.related_ids == ["CLAIM-2026-0001"]


# ── DriftSignal -> CERPA Review ─────────────────────────────────


class TestReviewFromDrift:
    def test_review_from_drift(self) -> None:
        drift = DriftSignal(
            drift_id="DRIFT-2026-0001",
            decision_id="DEC-2026-0001",
            trigger="half_life_expiry",
            detected_at="2026-03-02T10:05:00Z",
            severity="yellow",
            related_claims=["CLAIM-2026-0001"],
            description="Claim half-life expired",
        )
        review = review_from_drift(drift)
        assert review.id == "DRIFT-2026-0001"
        assert review.claim_id == "CLAIM-2026-0001"
        assert review.verdict == "mismatch"
        assert review.drift_detected is True
        assert review.severity == "yellow"
        assert review.metadata["trigger"] == "half_life_expiry"

    def test_review_from_drift_explicit_claim(self) -> None:
        drift = DriftSignal(
            drift_id="DRIFT-2026-0002",
            decision_id="DEC-2026-0002",
            trigger="contradiction",
            detected_at="2026-03-02T11:00:00Z",
        )
        review = review_from_drift(drift, claim_id="custom-claim", event_id="custom-event")
        assert review.claim_id == "custom-claim"
        assert review.event_id == "custom-event"


# ── Patch <-> canonical ─────────────────────────────────────────


class TestPatchMappers:
    def test_patch_from_canonical(self) -> None:
        canonical = CanonicalPatch(
            patch_id="PATCH-2026-0001",
            decision_id="DEC-2026-0001",
            drift_id="DRIFT-2026-0001",
            issued_at="2026-03-02T10:15:00Z",
            description="Increase auto-scaling max replicas",
            claims_updated=["CLAIM-2026-0001"],
            rationale="Claim expired",
            lineage={"rev": 1},
        )
        cerpa_patch = patch_from_canonical(canonical, review_id="rev-001")
        assert cerpa_patch.id == "PATCH-2026-0001"
        assert cerpa_patch.review_id == "rev-001"
        assert cerpa_patch.description == "Increase auto-scaling max replicas"
        assert cerpa_patch.metadata["rationale"] == "Claim expired"

    def test_patch_to_canonical(self) -> None:
        from core.cerpa.models import Patch as CerpaPatch

        cerpa_patch = CerpaPatch(
            id="PATCH-2026-0002",
            review_id="rev-002",
            domain="reops",
            timestamp="2026-03-02T10:20:00Z",
            action="adjust",
            target="DEC-2026-0002",
            description="Scale down after resolution",
            metadata={"rationale": "Drift resolved", "lineage": {"rev": 2}},
        )
        canonical = patch_to_canonical(cerpa_patch, decision_id="DEC-2026-0002", drift_id="DRIFT-2026-0002")
        assert canonical.patch_id == "PATCH-2026-0002"
        assert canonical.decision_id == "DEC-2026-0002"
        assert canonical.drift_id == "DRIFT-2026-0002"
        assert canonical.rationale == "Drift resolved"

    def test_patch_round_trip(self) -> None:
        canonical = CanonicalPatch(
            patch_id="PATCH-2026-0003",
            decision_id="DEC-2026-0003",
            drift_id="DRIFT-2026-0003",
            issued_at="2026-03-02T10:25:00Z",
            description="Refresh stale observation",
        )
        cerpa_patch = patch_from_canonical(canonical)
        roundtripped = patch_to_canonical(
            cerpa_patch,
            decision_id=canonical.decision_id,
            drift_id=canonical.drift_id,
        )
        assert roundtripped.patch_id == canonical.patch_id
        assert roundtripped.decision_id == canonical.decision_id
        assert roundtripped.drift_id == canonical.drift_id
        assert roundtripped.description == canonical.description


# ── DLR -> Review ───────────────────────────────────────────────


class TestReviewFromDLR:
    def test_review_from_dlr(self) -> None:
        from dataclasses import dataclass, field
        from typing import Any, Dict, List, Optional

        @dataclass
        class MockDLR:
            dlr_id: str = "dlr-abc123"
            episode_id: str = "ep-001"
            decision_type: str = "scale"
            recorded_at: str = "2026-03-01T11:00:00Z"
            outcome_code: str = "success"

        dlr = MockDLR()
        review = review_from_dlr(dlr)
        assert review.id == "dlr-abc123"
        assert review.event_id == "ep-001"
        assert review.verdict == "aligned"
        assert review.drift_detected is False
        assert review.metadata["decision_type"] == "scale"
