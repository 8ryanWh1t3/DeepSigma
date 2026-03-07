"""Tests for primitive records — typed payload contracts for PrimitiveEnvelope."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cerpa.models import ApplyResult, Claim, Event, Patch, Review
from core.primitives import PrimitiveType
from core.primitive_records import (
    ApplyRecord,
    ClaimRecord,
    EventRecord,
    PatchRecord,
    ReviewRecord,
    RECORD_TYPE_MAP,
    record_from_cerpa,
)
from core.primitive_envelope import wrap_record


# ── Fixtures ──────────────────────────────────────────────────────


def _cerpa_claim() -> Claim:
    return Claim(
        id="c-001",
        text="Latency stays below 200ms",
        domain="infra",
        source="monitor",
        timestamp="2026-01-01T00:00:00Z",
        assumptions=["stable traffic"],
        metadata={"tier": "gold"},
    )


def _cerpa_event() -> Event:
    return Event(
        id="e-001",
        text="Latency spike to 350ms",
        domain="infra",
        source="telemetry",
        timestamp="2026-01-01T00:05:00Z",
        observed_state={"p99_ms": 350},
        metadata={"region": "us-east-1"},
    )


def _cerpa_review() -> Review:
    return Review(
        id="r-001",
        claim_id="c-001",
        event_id="e-001",
        domain="infra",
        timestamp="2026-01-01T00:06:00Z",
        verdict="drifted",
        rationale="p99 exceeds 200ms threshold",
        drift_detected=True,
        severity="red",
        metadata={"auto": True},
    )


def _cerpa_patch() -> Patch:
    return Patch(
        id="p-001",
        review_id="r-001",
        domain="infra",
        timestamp="2026-01-01T00:07:00Z",
        action="scale_up",
        target="web-fleet",
        description="Add 2 replicas",
        metadata={"reason": "drift"},
    )


def _cerpa_apply() -> ApplyResult:
    return ApplyResult(
        id="a-001",
        patch_id="p-001",
        domain="infra",
        timestamp="2026-01-01T00:08:00Z",
        success=True,
        new_state={"replicas": 5},
        updated_claims=["c-001"],
        metadata={"elapsed_ms": 1200},
    )


# ── ClaimRecord ───────────────────────────────────────────────────


class TestClaimRecord:
    def test_primitive_type(self):
        assert ClaimRecord.PRIMITIVE_TYPE is PrimitiveType.CLAIM

    def test_from_cerpa(self):
        rec = ClaimRecord.from_cerpa(_cerpa_claim())
        assert rec.claim_id == "c-001"
        assert rec.text == "Latency stays below 200ms"
        assert rec.domain == "infra"
        assert rec.assumptions == ["stable traffic"]

    def test_to_dict_keys(self):
        rec = ClaimRecord.from_cerpa(_cerpa_claim())
        d = rec.to_dict()
        assert "claimId" in d
        assert "text" in d
        assert "domain" in d
        assert "source" in d
        assert "timestamp" in d
        assert "assumptions" in d

    def test_to_dict_optional_fields(self):
        rec = ClaimRecord(
            claim_id="c-002",
            text="test",
            domain="test",
            source="test",
            timestamp="2026-01-01T00:00:00Z",
        )
        d = rec.to_dict()
        assert "assumptions" not in d
        assert "confidence" not in d
        assert "metadata" not in d


# ── EventRecord ───────────────────────────────────────────────────


class TestEventRecord:
    def test_primitive_type(self):
        assert EventRecord.PRIMITIVE_TYPE is PrimitiveType.EVENT

    def test_from_cerpa(self):
        rec = EventRecord.from_cerpa(_cerpa_event())
        assert rec.event_id == "e-001"
        assert rec.observed_state == {"p99_ms": 350}

    def test_to_dict_keys(self):
        rec = EventRecord.from_cerpa(_cerpa_event())
        d = rec.to_dict()
        assert "eventId" in d
        assert "observedState" in d


# ── ReviewRecord ──────────────────────────────────────────────────


class TestReviewRecord:
    def test_primitive_type(self):
        assert ReviewRecord.PRIMITIVE_TYPE is PrimitiveType.REVIEW

    def test_from_cerpa(self):
        rec = ReviewRecord.from_cerpa(_cerpa_review())
        assert rec.review_id == "r-001"
        assert rec.claim_id == "c-001"
        assert rec.event_id == "e-001"
        assert rec.drift_detected is True
        assert rec.severity == "red"

    def test_to_dict_keys(self):
        rec = ReviewRecord.from_cerpa(_cerpa_review())
        d = rec.to_dict()
        assert "reviewId" in d
        assert "claimId" in d
        assert "eventId" in d
        assert "driftDetected" in d
        assert "severity" in d


# ── PatchRecord ───────────────────────────────────────────────────


class TestPatchRecord:
    def test_primitive_type(self):
        assert PatchRecord.PRIMITIVE_TYPE is PrimitiveType.PATCH

    def test_from_cerpa(self):
        rec = PatchRecord.from_cerpa(_cerpa_patch())
        assert rec.patch_id == "p-001"
        assert rec.review_id == "r-001"
        assert rec.action == "scale_up"

    def test_to_dict_keys(self):
        rec = PatchRecord.from_cerpa(_cerpa_patch())
        d = rec.to_dict()
        assert "patchId" in d
        assert "reviewId" in d
        assert "action" in d
        assert "target" in d


# ── ApplyRecord ───────────────────────────────────────────────────


class TestApplyRecord:
    def test_primitive_type(self):
        assert ApplyRecord.PRIMITIVE_TYPE is PrimitiveType.APPLY

    def test_from_cerpa(self):
        rec = ApplyRecord.from_cerpa(_cerpa_apply())
        assert rec.apply_id == "a-001"
        assert rec.patch_id == "p-001"
        assert rec.success is True
        assert rec.new_state == {"replicas": 5}
        assert rec.updated_claims == ["c-001"]

    def test_to_dict_keys(self):
        rec = ApplyRecord.from_cerpa(_cerpa_apply())
        d = rec.to_dict()
        assert "applyId" in d
        assert "patchId" in d
        assert "success" in d
        assert "newState" in d
        assert "updatedClaims" in d


# ── Registry ──────────────────────────────────────────────────────


class TestRecordTypeMap:
    def test_maps_all_five_types(self):
        assert set(RECORD_TYPE_MAP.keys()) == set(PrimitiveType)

    def test_correct_classes(self):
        assert RECORD_TYPE_MAP[PrimitiveType.CLAIM] is ClaimRecord
        assert RECORD_TYPE_MAP[PrimitiveType.EVENT] is EventRecord
        assert RECORD_TYPE_MAP[PrimitiveType.REVIEW] is ReviewRecord
        assert RECORD_TYPE_MAP[PrimitiveType.PATCH] is PatchRecord
        assert RECORD_TYPE_MAP[PrimitiveType.APPLY] is ApplyRecord


class TestRecordFromCerpa:
    def test_claim(self):
        rec = record_from_cerpa(PrimitiveType.CLAIM, _cerpa_claim())
        assert isinstance(rec, ClaimRecord)

    def test_event(self):
        rec = record_from_cerpa(PrimitiveType.EVENT, _cerpa_event())
        assert isinstance(rec, EventRecord)

    def test_unknown_type_raises(self):
        with pytest.raises(KeyError):
            record_from_cerpa("bogus", object())


# ── wrap_record integration ───────────────────────────────────────


class TestWrapRecord:
    def test_produces_valid_envelope(self):
        rec = ClaimRecord.from_cerpa(_cerpa_claim())
        env = wrap_record(rec, source="test-harness")
        assert env.primitive_type is PrimitiveType.CLAIM
        assert env.payload["claimId"] == "c-001"
        assert env.source == "test-harness"

    def test_each_record_type_wraps(self):
        pairs = [
            (ClaimRecord.from_cerpa(_cerpa_claim()), PrimitiveType.CLAIM),
            (EventRecord.from_cerpa(_cerpa_event()), PrimitiveType.EVENT),
            (ReviewRecord.from_cerpa(_cerpa_review()), PrimitiveType.REVIEW),
            (PatchRecord.from_cerpa(_cerpa_patch()), PrimitiveType.PATCH),
            (ApplyRecord.from_cerpa(_cerpa_apply()), PrimitiveType.APPLY),
        ]
        for rec, expected_type in pairs:
            env = wrap_record(rec, source="test")
            assert env.primitive_type is expected_type
            assert isinstance(env.payload, dict)

    def test_metadata_passthrough(self):
        rec = EventRecord.from_cerpa(_cerpa_event())
        env = wrap_record(rec, source="test", metadata={"tag": "ci"})
        assert env.metadata == {"tag": "ci"}


# ── Schema validation ────────────────────────────────────────────


class TestApplySchemaFixture:
    """Validate apply_example.json against apply.schema.json."""

    def test_fixture_validates_against_schema(self):
        import json
        import jsonschema

        schema_path = _SRC_ROOT / "core" / "schemas" / "primitives" / "apply.schema.json"
        fixture_path = _SRC_ROOT / "core" / "fixtures" / "primitives" / "apply_example.json"
        schema = json.loads(schema_path.read_text())
        fixture = json.loads(fixture_path.read_text())
        jsonschema.validate(fixture, schema)

    def test_apply_record_to_dict_validates(self):
        import json
        import jsonschema

        schema_path = _SRC_ROOT / "core" / "schemas" / "primitives" / "apply.schema.json"
        schema = json.loads(schema_path.read_text())
        rec = ApplyRecord.from_cerpa(_cerpa_apply())
        jsonschema.validate(rec.to_dict(), schema)
