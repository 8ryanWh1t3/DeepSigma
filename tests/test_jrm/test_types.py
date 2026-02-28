"""Tests for JRM core types."""

from __future__ import annotations

from core.jrm.types import (
    Claim,
    DecisionLane,
    DriftDetection,
    EventType,
    JRMDriftType,
    JRMEvent,
    PacketManifest,
    PatchRecord,
    PipelineResult,
    ReasoningResult,
    Severity,
    WhyBullet,
)


class TestEnums:
    def test_event_type_members(self):
        assert EventType.SURICATA_ALERT.value == "suricata_alert"
        assert EventType.MALFORMED.value == "malformed"
        assert len(EventType) == 11

    def test_severity_members(self):
        assert Severity.CRITICAL.value == "critical"
        assert len(Severity) == 5

    def test_decision_lane_members(self):
        assert DecisionLane.LOG_ONLY.value == "LOG_ONLY"
        assert DecisionLane.REQUIRE_REVIEW.value == "REQUIRE_REVIEW"
        assert len(DecisionLane) == 4

    def test_drift_type_members(self):
        assert JRMDriftType.FP_SPIKE.value == "FP_SPIKE"
        assert len(JRMDriftType) == 4


class TestJRMEvent:
    def test_construction(self):
        event = JRMEvent(
            event_id="JRM-001",
            source_system="suricata",
            event_type=EventType.SURICATA_ALERT,
            timestamp="2026-02-28T10:00:00Z",
            severity=Severity.HIGH,
            actor={"type": "host", "id": "10.0.0.1"},
            object={"type": "host", "id": "10.0.0.2"},
            action="alert:sid=2010935:rev=6",
            confidence=0.85,
            evidence_hash="sha256:" + "a" * 64,
            raw_pointer="inline:sha256:" + "a" * 64,
            environment_id="test",
        )
        assert event.event_id == "JRM-001"
        assert event.assumptions == []
        assert event.metadata == {}

    def test_to_dict(self):
        event = JRMEvent(
            event_id="JRM-001",
            source_system="suricata",
            event_type=EventType.SURICATA_ALERT,
            timestamp="2026-02-28T10:00:00Z",
            severity=Severity.HIGH,
            actor={"type": "host", "id": "10.0.0.1"},
            object={"type": "host", "id": "10.0.0.2"},
            action="alert",
            confidence=0.85,
            evidence_hash="sha256:" + "a" * 64,
            raw_pointer="test",
            environment_id="env1",
        )
        d = event.to_dict()
        assert d["eventId"] == "JRM-001"
        assert d["eventType"] == "suricata_alert"
        assert d["severity"] == "high"

    def test_defaults(self):
        event = JRMEvent(
            event_id="x", source_system="s", event_type=EventType.GENERIC,
            timestamp="t", severity=Severity.INFO, actor={"type": "a", "id": "a"},
            object={"type": "o", "id": "o"}, action="a", confidence=0.5,
            evidence_hash="sha256:" + "0" * 64, raw_pointer="p",
            environment_id="e",
        )
        assert event.raw_bytes == b""
        assert event.assumptions == []
        assert event.metadata == {}


class TestClaim:
    def test_construction(self):
        c = Claim(
            claim_id="CLM-001", statement="test", confidence=0.9,
            evidence_refs=["ref1"], source_events=["ev1"],
            timestamp="2026-02-28T10:00:00Z",
        )
        assert c.claim_id == "CLM-001"
        assert c.assumptions == []


class TestPatchRecord:
    def test_lineage(self):
        p = PatchRecord(
            patch_id="P-002", drift_id="D-001", rev=2, previous_rev=1,
            changes=[{"field": "severity", "old": "low", "new": "high"}],
            applied_at="2026-02-28T10:00:00Z",
            supersedes="P-001",
            lineage=["P-001"],
        )
        assert p.rev == 2
        assert p.supersedes == "P-001"
        assert p.lineage == ["P-001"]


class TestPipelineResult:
    def test_defaults(self):
        r = PipelineResult(
            environment_id="env", events_processed=10,
            window_start="2026-02-28T10:00:00Z",
            window_end="2026-02-28T10:10:00Z",
        )
        assert r.claims == []
        assert r.errors == []
        assert r.mg_deltas == {}
