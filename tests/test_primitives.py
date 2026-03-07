"""Unit tests for core.primitives — canonical core primitive dataclasses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.primitives import (  # noqa: E402
    ALLOWED_PRIMITIVE_TYPES,
    AtomicClaim,
    ClaimLifecycle,
    DecisionEpisode,
    DriftSeverity,
    DriftSignal,
    DriftStatus,
    EpisodeStatus,
    Patch,
    PatchStatus,
    PrimitiveType,
    validate_claim,
    validate_drift,
    validate_episode,
    validate_patch,
)
from core.schema_validator import clear_cache  # noqa: E402

FIXTURES_DIR = _SRC_ROOT / "core" / "fixtures" / "primitives"


# ── Factories ────────────────────────────────────────────────────


def _make_claim(**overrides: object) -> AtomicClaim:
    defaults = dict(
        claim_id="CLAIM-2026-0001",
        claim_type="observation",
        statement="System latency p99 is under 200ms for the payments service",
        source="apm-monitor-001",
        confidence=0.92,
        created_at="2026-03-01T10:00:00Z",
    )
    defaults.update(overrides)
    return AtomicClaim(**defaults)  # type: ignore[arg-type]


def _make_episode(**overrides: object) -> DecisionEpisode:
    defaults = dict(
        decision_id="DEC-2026-0001",
        title="Scale service to meet SLA",
        owner="platform-ops",
        created_at="2026-03-01T10:30:00Z",
        goal="Maintain p99 < 200ms",
    )
    defaults.update(overrides)
    return DecisionEpisode(**defaults)  # type: ignore[arg-type]


def _make_drift(**overrides: object) -> DriftSignal:
    defaults = dict(
        drift_id="DRIFT-2026-0001",
        decision_id="DEC-2026-0001",
        trigger="half_life_expiry",
        detected_at="2026-03-02T10:05:00Z",
    )
    defaults.update(overrides)
    return DriftSignal(**defaults)  # type: ignore[arg-type]


def _make_patch(**overrides: object) -> Patch:
    defaults = dict(
        patch_id="PATCH-2026-0001",
        decision_id="DEC-2026-0001",
        drift_id="DRIFT-2026-0001",
        issued_at="2026-03-02T10:15:00Z",
        description="Increase auto-scaling max replicas",
    )
    defaults.update(overrides)
    return Patch(**defaults)  # type: ignore[arg-type]


# ── Enum tests ───────────────────────────────────────────────────


class TestEnums:
    def test_claim_lifecycle_values(self) -> None:
        assert set(ClaimLifecycle) == {
            ClaimLifecycle.ACTIVE,
            ClaimLifecycle.EXPIRED,
            ClaimLifecycle.SUPERSEDED,
            ClaimLifecycle.DISPUTED,
            ClaimLifecycle.RETRACTED,
        }
        assert ClaimLifecycle.ACTIVE.value == "active"
        assert isinstance(ClaimLifecycle.ACTIVE, str)

    def test_episode_status_values(self) -> None:
        assert EpisodeStatus.SEALED.value == "sealed"
        assert isinstance(EpisodeStatus.PENDING, str)

    def test_drift_severity_values(self) -> None:
        assert DriftSeverity.RED.value == "red"
        assert isinstance(DriftSeverity.GREEN, str)

    def test_drift_status_values(self) -> None:
        assert DriftStatus.DETECTED.value == "detected"
        assert isinstance(DriftStatus.RESOLVED, str)

    def test_patch_status_values(self) -> None:
        assert PatchStatus.APPLIED.value == "applied"
        assert isinstance(PatchStatus.SUPERSEDED, str)

    def test_primitive_type_has_five_members(self) -> None:
        assert len(PrimitiveType) == 5

    def test_primitive_type_values(self) -> None:
        assert {p.value for p in PrimitiveType} == {
            "claim", "event", "review", "patch", "apply",
        }

    def test_allowed_primitive_types_is_frozenset(self) -> None:
        assert isinstance(ALLOWED_PRIMITIVE_TYPES, frozenset)
        assert len(ALLOWED_PRIMITIVE_TYPES) == 5


# ── AtomicClaim tests ────────────────────────────────────────────


class TestAtomicClaim:
    def test_create_with_defaults(self) -> None:
        c = _make_claim()
        assert c.claim_id == "CLAIM-2026-0001"
        assert c.status == "active"
        assert c.supports == []
        assert c.contradicts == []
        assert c.tags == []
        assert c.metadata == {}
        assert c.expires_at is None

    def test_to_dict_camel_case(self) -> None:
        c = _make_claim(tags=["sla"], supports=["CLAIM-2026-0002"])
        d = c.to_dict()
        assert "claimId" in d
        assert "claimType" in d
        assert "createdAt" in d
        assert d["tags"] == ["sla"]
        assert d["supports"] == ["CLAIM-2026-0002"]
        # snake_case keys must not appear
        assert "claim_id" not in d
        assert "claim_type" not in d
        assert "created_at" not in d

    def test_from_dict_round_trip(self) -> None:
        c = _make_claim(
            tags=["latency"],
            provenance=[{"type": "source", "ref": "apm-001"}],
            expires_at="2026-04-01T00:00:00Z",
        )
        d = c.to_dict()
        c2 = AtomicClaim.from_dict(d)
        assert c2.claim_id == c.claim_id
        assert c2.claim_type == c.claim_type
        assert c2.tags == c.tags
        assert c2.provenance == c.provenance
        assert c2.expires_at == c.expires_at
        assert c2.to_dict() == d

    def test_seal_hash_deterministic(self) -> None:
        c = _make_claim()
        h1 = c.seal_hash()
        h2 = c.seal_hash()
        assert h1 == h2
        assert h1.startswith("sha256:")
        assert len(h1) == len("sha256:") + 64

    def test_seal_hash_changes_with_data(self) -> None:
        c1 = _make_claim(confidence=0.90)
        c2 = _make_claim(confidence=0.50)
        assert c1.seal_hash() != c2.seal_hash()

    def test_is_expired_past(self) -> None:
        c = _make_claim(expires_at="2020-01-01T00:00:00Z")
        assert c.is_expired() is True

    def test_is_expired_future(self) -> None:
        c = _make_claim(expires_at="2099-01-01T00:00:00Z")
        assert c.is_expired() is False

    def test_is_expired_none(self) -> None:
        c = _make_claim(expires_at=None)
        assert c.is_expired() is False

    def test_schema_validation_valid(self) -> None:
        clear_cache()
        c = _make_claim()
        result = validate_claim(c.to_dict())
        assert result.valid, f"Errors: {result.errors}"

    def test_schema_validation_invalid(self) -> None:
        clear_cache()
        result = validate_claim({"bad": True})
        assert not result.valid


# ── DecisionEpisode tests ────────────────────────────────────────


class TestDecisionEpisode:
    def test_create_with_defaults(self) -> None:
        ep = _make_episode()
        assert ep.decision_id == "DEC-2026-0001"
        assert ep.status == "pending"
        assert ep.claims_used == []
        assert ep.options == []
        assert ep.outcome is None

    def test_to_dict_camel_case(self) -> None:
        ep = _make_episode(
            claims_used=["CLAIM-2026-0001"],
            selected_option="opt-1",
            blast_radius="service",
        )
        d = ep.to_dict()
        assert "decisionId" in d
        assert "createdAt" in d
        assert d["claimsUsed"] == ["CLAIM-2026-0001"]
        assert d["selectedOption"] == "opt-1"
        assert d["blastRadius"] == "service"
        assert "decision_id" not in d

    def test_from_dict_round_trip(self) -> None:
        ep = _make_episode(
            claims_used=["CLAIM-2026-0001"],
            options=[{"id": "opt-1", "description": "Scale up"}],
            selected_option="opt-1",
            outcome={"code": "success"},
        )
        d = ep.to_dict()
        ep2 = DecisionEpisode.from_dict(d)
        assert ep2.to_dict() == d

    def test_seal_hash_deterministic(self) -> None:
        ep = _make_episode()
        h1 = ep.seal_hash()
        h2 = ep.seal_hash()
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_schema_validation_valid(self) -> None:
        clear_cache()
        ep = _make_episode()
        result = validate_episode(ep.to_dict())
        assert result.valid, f"Errors: {result.errors}"

    def test_schema_validation_invalid(self) -> None:
        clear_cache()
        result = validate_episode({})
        assert not result.valid


# ── DriftSignal tests ────────────────────────────────────────────


class TestDriftSignal:
    def test_create_with_defaults(self) -> None:
        ds = _make_drift()
        assert ds.drift_id == "DRIFT-2026-0001"
        assert ds.severity == "yellow"
        assert ds.status == "detected"
        assert ds.related_claims == []
        assert ds.telemetry_refs == []

    def test_to_dict_camel_case(self) -> None:
        ds = _make_drift(
            related_claims=["CLAIM-2026-0001"],
            expected_state="p99 < 200ms",
            observed_state="p99 = 280ms",
        )
        d = ds.to_dict()
        assert "driftId" in d
        assert "decisionId" in d
        assert "detectedAt" in d
        assert d["relatedClaims"] == ["CLAIM-2026-0001"]
        assert d["expectedState"] == "p99 < 200ms"
        assert "drift_id" not in d

    def test_from_dict_round_trip(self) -> None:
        ds = _make_drift(
            related_claims=["CLAIM-2026-0001"],
            description="Latency exceeded SLA",
            severity="red",
        )
        d = ds.to_dict()
        ds2 = DriftSignal.from_dict(d)
        assert ds2.to_dict() == d

    def test_schema_validation_valid(self) -> None:
        clear_cache()
        ds = _make_drift()
        result = validate_drift(ds.to_dict())
        assert result.valid, f"Errors: {result.errors}"

    def test_schema_validation_invalid(self) -> None:
        clear_cache()
        result = validate_drift({"bad": True})
        assert not result.valid


# ── Patch tests ──────────────────────────────────────────────────


class TestPatch:
    def test_create_with_defaults(self) -> None:
        p = _make_patch()
        assert p.patch_id == "PATCH-2026-0001"
        assert p.status == "proposed"
        assert p.claims_updated == []
        assert p.supersedes == []
        assert p.rationale == ""

    def test_to_dict_camel_case(self) -> None:
        p = _make_patch(
            claims_updated=["CLAIM-2026-0001"],
            rationale="Claim expired",
            lineage={"rev": 1},
        )
        d = p.to_dict()
        assert "patchId" in d
        assert "decisionId" in d
        assert "driftId" in d
        assert "issuedAt" in d
        assert d["claimsUpdated"] == ["CLAIM-2026-0001"]
        assert d["rationale"] == "Claim expired"
        assert d["lineage"] == {"rev": 1}
        assert "patch_id" not in d

    def test_from_dict_round_trip(self) -> None:
        p = _make_patch(
            claims_updated=["CLAIM-2026-0001"],
            supersedes=["PATCH-2026-0000"],
            status="applied",
        )
        d = p.to_dict()
        p2 = Patch.from_dict(d)
        assert p2.to_dict() == d

    def test_schema_validation_valid(self) -> None:
        clear_cache()
        p = _make_patch()
        result = validate_patch(p.to_dict())
        assert result.valid, f"Errors: {result.errors}"

    def test_schema_validation_invalid(self) -> None:
        clear_cache()
        result = validate_patch({})
        assert not result.valid


# ── Lifecycle integration test ───────────────────────────────────


class TestLifecycle:
    def test_claim_to_decision_to_drift_to_patch(self) -> None:
        """Full lifecycle: claim -> decision -> drift -> patch."""
        # 1. Analyst observes anomaly
        claim = _make_claim(
            claim_id="CLAIM-2026-1000",
            statement="Fraud detection model accuracy dropped below 90% threshold",
            claim_type="observation",
            confidence=0.88,
            expires_at="2026-03-02T10:00:00Z",
        )

        # 2. Decision references the claim
        episode = _make_episode(
            decision_id="DEC-2026-1000",
            title="Retrain fraud model with latest dataset",
            claims_used=[claim.claim_id],
            options=[
                {"id": "retrain", "description": "Full retrain with Q1 data"},
                {"id": "finetune", "description": "Fine-tune with recent samples"},
            ],
            selected_option="retrain",
            rejected_options=["finetune"],
            assumptions=["Training data is representative of current patterns"],
            status="sealed",
            outcome={"code": "success", "reason": "Model retrained, accuracy 94%"},
        )

        # 3. Drift detected — claim half-life expired
        drift = _make_drift(
            drift_id="DRIFT-2026-1000",
            decision_id=episode.decision_id,
            related_claims=[claim.claim_id],
            trigger="half_life_expiry",
            severity="yellow",
            description="Claim half-life expired; accuracy may have degraded",
            expected_state="accuracy >= 90%",
            observed_state="accuracy unknown (stale claim)",
        )

        # 4. Patch resolves the drift
        patch = _make_patch(
            patch_id="PATCH-2026-1000",
            decision_id=episode.decision_id,
            drift_id=drift.drift_id,
            description="Re-evaluate model accuracy and refresh claim",
            claims_updated=[claim.claim_id],
            status="applied",
            rationale="Claim expired — need fresh observation",
            lineage={"rev": 1, "drift_ref": drift.drift_id},
        )

        # Verify cross-references
        assert claim.claim_id in episode.claims_used
        assert episode.decision_id == drift.decision_id
        assert claim.claim_id in drift.related_claims
        assert drift.drift_id == patch.drift_id
        assert episode.decision_id == patch.decision_id
        assert claim.claim_id in patch.claims_updated

        # Verify round-trip integrity for all four
        for obj in [claim, episode, drift, patch]:
            d = obj.to_dict()
            reconstructed = type(obj).from_dict(d)
            assert reconstructed.to_dict() == d

        # Verify all pass schema validation
        clear_cache()
        assert validate_claim(claim.to_dict()).valid
        assert validate_episode(episode.to_dict()).valid
        assert validate_drift(drift.to_dict()).valid
        assert validate_patch(patch.to_dict()).valid


# ── Fixture loading tests ────────────────────────────────────────


class TestFixtures:
    def test_load_claim_fixture(self) -> None:
        clear_cache()
        data = json.loads((FIXTURES_DIR / "atomic_claim_example.json").read_text())
        claim = AtomicClaim.from_dict(data)
        assert claim.claim_id == "CLAIM-2026-0100"
        result = validate_claim(data)
        assert result.valid, f"Errors: {result.errors}"

    def test_load_episode_fixture(self) -> None:
        clear_cache()
        data = json.loads((FIXTURES_DIR / "decision_episode_example.json").read_text())
        ep = DecisionEpisode.from_dict(data)
        assert ep.decision_id == "DEC-2026-0100"
        result = validate_episode(data)
        assert result.valid, f"Errors: {result.errors}"

    def test_load_drift_fixture(self) -> None:
        clear_cache()
        data = json.loads((FIXTURES_DIR / "drift_signal_example.json").read_text())
        ds = DriftSignal.from_dict(data)
        assert ds.drift_id == "DRIFT-2026-0100"
        result = validate_drift(data)
        assert result.valid, f"Errors: {result.errors}"

    def test_load_patch_fixture(self) -> None:
        clear_cache()
        data = json.loads((FIXTURES_DIR / "patch_example.json").read_text())
        p = Patch.from_dict(data)
        assert p.patch_id == "PATCH-2026-0100"
        result = validate_patch(data)
        assert result.valid, f"Errors: {result.errors}"
