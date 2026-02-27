"""Tests for FEEDS consumers — authority gate, evidence check, triage store."""

import json

import pytest

from core.feeds.consumers import (
    AuthorityGateConsumer,
    EvidenceCheckConsumer,
    TriageEntry,
    TriageState,
    TriageStore,
)


# ── Helpers ───────────────────────────────────────────────────────

def _make_dlr_payload(action_claims=None, context_claims=None):
    """Build a minimal DLR payload."""
    if action_claims is None:
        action_claims = [{"claimId": "ACT-001"}, {"claimId": "ACT-002"}]
    if context_claims is None:
        context_claims = [{"claimId": "CTX-001"}]
    return {
        "dlrId": "DLR-aabbccddee01",
        "episodeId": "ep-test-001",
        "decisionType": "AccountQuarantine",
        "recordedAt": "2026-02-27T10:00:00Z",
        "claims": {
            "context": context_claims,
            "rationale": [],
            "action": action_claims,
            "verification": [],
            "outcome": [],
        },
        "rationaleGraph": {"edges": []},
        "outcome": {"code": "success"},
        "dteRef": {"decisionType": "AccountQuarantine", "version": "1.0"},
        "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
    }


def _make_als_payload(blessed=None):
    """Build a minimal ALS payload."""
    return {
        "sliceId": "ALS-test-001",
        "authoritySource": "governance-engine",
        "authorityRole": "policy-owner",
        "scope": "security-operations",
        "claimsBlessed": blessed or ["ACT-001", "ACT-002"],
        "effectiveAt": "2026-02-27T09:00:00Z",
        "seal": {"hash": "sha256:als", "sealedAt": "2026-02-27T09:00:01Z", "version": 1},
    }


def _make_manifest_payload(event_ids=None):
    """Build a minimal packet_index payload."""
    artifacts = []
    for eid in (event_ids or []):
        artifacts.append({
            "topic": "truth_snapshot",
            "recordType": "TS",
            "eventId": eid,
            "payloadHash": "sha256:" + "a" * 64,
        })
    return {
        "packetId": "CP-2026-02-27-0001",
        "createdAt": "2026-02-27T12:00:00Z",
        "producer": "test",
        "artifactManifest": artifacts,
        "totalEvents": len(artifacts),
        "seal": {"hash": "sha256:pi", "sealedAt": "2026-02-27T12:00:01Z", "version": 1},
    }


def _make_drift_event(drift_id="DS-test-001", drift_type="freshness", severity="yellow"):
    """Build a minimal drift signal event (full envelope shape)."""
    return {
        "eventId": "evt-001",
        "packetId": "CP-2026-02-27-0001",
        "topic": "drift_signal",
        "payload": {
            "driftId": drift_id,
            "driftType": drift_type,
            "severity": severity,
            "detectedAt": "2026-02-27T11:00:00Z",
            "evidenceRefs": ["ref-001"],
            "recommendedPatchType": "ttl_change",
            "fingerprint": {"key": "test:key", "version": "1"},
            "notes": "Test drift signal.",
        },
    }


# ── Authority Gate Tests ──────────────────────────────────────────

class TestAuthorityGate:
    def test_mismatch_detected(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[
            {"claimId": "ACT-001"},
            {"claimId": "ACT-ROGUE"},
        ])
        als = _make_als_payload(blessed=["ACT-001"])
        result = gate.check(dlr, [als])

        assert result is not None
        assert result["driftType"] == "authority_mismatch"
        assert result["severity"] == "red"
        assert "ACT-ROGUE" in result["notes"]

    def test_no_mismatch(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[{"claimId": "ACT-001"}])
        als = _make_als_payload(blessed=["ACT-001", "ACT-002"])
        result = gate.check(dlr, [als])

        assert result is None

    def test_empty_als_detects_all_unblessed(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[
            {"claimId": "ACT-001"},
            {"claimId": "ACT-002"},
        ])
        result = gate.check(dlr, [])

        assert result is not None
        assert result["driftType"] == "authority_mismatch"
        assert "ACT-001" in result["notes"]
        assert "ACT-002" in result["notes"]

    def test_drift_format_valid(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[{"claimId": "ACT-ROGUE"}])
        result = gate.check(dlr, [])

        assert "driftId" in result
        assert "fingerprint" in result
        assert result["recommendedPatchType"] == "authority_update"

    def test_no_action_claims_returns_none(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[])
        result = gate.check(dlr, [_make_als_payload()])
        assert result is None

    def test_multiple_als_slices(self):
        gate = AuthorityGateConsumer()
        dlr = _make_dlr_payload(action_claims=[
            {"claimId": "ACT-001"},
            {"claimId": "ACT-002"},
        ])
        als1 = _make_als_payload(blessed=["ACT-001"])
        als2 = _make_als_payload(blessed=["ACT-002"])
        result = gate.check(dlr, [als1, als2])

        assert result is None  # both claims blessed across two slices


# ── Evidence Check Tests ──────────────────────────────────────────

class TestEvidenceCheck:
    def test_missing_refs_detected(self):
        checker = EvidenceCheckConsumer()
        dlr = _make_dlr_payload(context_claims=[
            {"claimId": "EVD-001"},
            {"claimId": "EVD-MISSING"},
        ])
        manifest = _make_manifest_payload(event_ids=["EVD-001"])
        result = checker.check(dlr, manifest)

        assert result is not None
        assert result["driftType"] == "process_gap"
        assert "EVD-MISSING" in result["notes"]

    def test_complete_returns_none(self):
        checker = EvidenceCheckConsumer()
        dlr = _make_dlr_payload(context_claims=[{"claimId": "EVD-001"}])
        manifest = _make_manifest_payload(event_ids=["EVD-001"])
        result = checker.check(dlr, manifest)

        assert result is None

    def test_drift_format_valid(self):
        checker = EvidenceCheckConsumer()
        dlr = _make_dlr_payload(context_claims=[{"claimId": "EVD-MISSING"}])
        manifest = _make_manifest_payload(event_ids=[])
        result = checker.check(dlr, manifest)

        assert "driftId" in result
        assert result["recommendedPatchType"] == "process_fix"
        assert result["severity"] == "yellow"

    def test_no_context_claims_returns_none(self):
        checker = EvidenceCheckConsumer()
        dlr = _make_dlr_payload(context_claims=[])
        manifest = _make_manifest_payload(event_ids=["EVD-001"])
        result = checker.check(dlr, manifest)

        assert result is None


# ── Triage Store Tests ────────────────────────────────────────────

class TestTriageStore:
    def test_ingest_creates_new_entry(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        event = _make_drift_event("DS-001")
        entry = store.ingest_drift(event)
        store.close()

        assert entry.drift_id == "DS-001"
        assert entry.state == TriageState.NEW
        assert entry.severity == "yellow"

    def test_full_transition_chain(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-002"))

        entry = store.set_state("DS-002", TriageState.TRIAGED, notes="Reviewed")
        assert entry.state == TriageState.TRIAGED

        entry = store.set_state("DS-002", TriageState.PATCH_PLANNED)
        assert entry.state == TriageState.PATCH_PLANNED

        entry = store.set_state("DS-002", TriageState.PATCHED)
        assert entry.state == TriageState.PATCHED

        entry = store.set_state("DS-002", TriageState.VERIFIED)
        assert entry.state == TriageState.VERIFIED
        store.close()

    def test_invalid_transition_raises(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-003"))

        with pytest.raises(ValueError, match="Invalid transition"):
            store.set_state("DS-003", TriageState.PATCHED)
        store.close()

    def test_missing_drift_id_raises(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        with pytest.raises(KeyError, match="not found"):
            store.set_state("DS-NONEXISTENT", TriageState.TRIAGED)
        store.close()

    def test_list_entries(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-A"))
        store.ingest_drift(_make_drift_event("DS-B", severity="red"))

        all_entries = store.list_entries()
        assert len(all_entries) == 2

        new_entries = store.list_entries(state=TriageState.NEW)
        assert len(new_entries) == 2
        store.close()

    def test_list_filter_by_state(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-X"))
        store.ingest_drift(_make_drift_event("DS-Y"))
        store.set_state("DS-X", TriageState.TRIAGED)

        triaged = store.list_entries(state=TriageState.TRIAGED)
        assert len(triaged) == 1
        assert triaged[0].drift_id == "DS-X"
        store.close()

    def test_stats(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-S1", severity="red"))
        store.ingest_drift(_make_drift_event("DS-S2", severity="yellow"))
        store.set_state("DS-S1", TriageState.TRIAGED)

        stats = store.stats()
        assert stats["total"] == 2
        assert stats["by_state"]["NEW"] == 1
        assert stats["by_state"]["TRIAGED"] == 1
        assert stats["by_severity"]["red"] == 1
        assert stats["by_severity"]["yellow"] == 1
        store.close()

    def test_notes_persisted(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-N1"))
        store.set_state("DS-N1", TriageState.TRIAGED, notes="First review")

        entry = store.get("DS-N1")
        assert "First review" in entry.notes
        store.close()

    def test_set_state_with_string(self, tmp_path):
        store = TriageStore(tmp_path / "triage.db")
        store.ingest_drift(_make_drift_event("DS-STR"))
        entry = store.set_state("DS-STR", "TRIAGED")
        assert entry.state == TriageState.TRIAGED
        store.close()

    def test_persistence_across_connections(self, tmp_path):
        db = tmp_path / "persist.db"
        store1 = TriageStore(db)
        store1.ingest_drift(_make_drift_event("DS-P1"))
        store1.close()

        store2 = TriageStore(db)
        entry = store2.get("DS-P1")
        assert entry is not None
        assert entry.drift_id == "DS-P1"
        store2.close()
