"""Tests for JRM pipeline stages."""

from __future__ import annotations

from core.jrm.types import (
    Claim,
    DecisionLane,
    DriftDetection,
    EventType,
    JRMDriftType,
    JRMEvent,
    PatchRecord,
    Severity,
)
from core.jrm.pipeline.truth import TruthStage
from core.jrm.pipeline.reasoning import ReasoningStage
from core.jrm.pipeline.drift import DriftStage
from core.jrm.pipeline.patch import PatchStage
from core.jrm.pipeline.memory_graph import MemoryGraphStage
from core.jrm.pipeline.runner import PipelineRunner


def _make_event(
    event_id="JRM-001",
    severity=Severity.HIGH,
    confidence=0.85,
    sig_id=2010935,
    rev=6,
    **kw,
) -> JRMEvent:
    defaults = dict(
        event_id=event_id,
        source_system="suricata",
        event_type=EventType.SURICATA_ALERT,
        timestamp="2026-02-28T10:00:00Z",
        severity=severity,
        actor={"type": "host", "id": "10.0.0.1"},
        object={"type": "host", "id": "10.0.0.2"},
        action=f"alert:sid={sig_id}:rev={rev}",
        confidence=confidence,
        evidence_hash="sha256:" + "a" * 64,
        raw_pointer="test",
        environment_id="test-env",
        metadata={"signature_id": sig_id, "rev": rev},
    )
    defaults.update(kw)
    return JRMEvent(**defaults)


class TestTruthStage:
    def test_clusters_by_signature(self):
        events = [
            _make_event("E1", sig_id=100),
            _make_event("E2", sig_id=100),
            _make_event("E3", sig_id=200),
        ]
        result = TruthStage().process(events)
        assert len(result.claims) == 2
        # sig:100 cluster should have 2 source events
        sig100 = [c for c in result.claims if "100" in c.statement]
        assert len(sig100) == 1
        assert len(sig100[0].source_events) == 2

    def test_truth_snapshot(self):
        events = [_make_event("E1"), _make_event("E2")]
        result = TruthStage().process(events)
        ts = result.truth_snapshot
        assert ts["event_count"] == 2
        assert ts["claim_count"] == 1
        assert "high" in ts["severity_histogram"]

    def test_empty_events(self):
        result = TruthStage().process([])
        assert result.claims == []
        assert result.truth_snapshot["event_count"] == 0


class TestReasoningStage:
    def test_require_review_lane(self):
        events = [_make_event("E1", severity=Severity.CRITICAL, confidence=0.95)]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert out.results[0].lane == DecisionLane.REQUIRE_REVIEW

    def test_queue_patch_lane(self):
        events = [_make_event("E1", severity=Severity.HIGH, confidence=0.5)]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert out.results[0].lane == DecisionLane.QUEUE_PATCH

    def test_notify_lane(self):
        events = [_make_event("E1", severity=Severity.MEDIUM, confidence=0.65)]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert out.results[0].lane == DecisionLane.NOTIFY

    def test_log_only_lane(self):
        events = [_make_event("E1", severity=Severity.LOW, confidence=0.3)]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert out.results[0].lane == DecisionLane.LOG_ONLY

    def test_why_bullets_present(self):
        events = [_make_event("E1")]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert len(out.results[0].why_bullets) >= 1
        assert out.results[0].why_bullets[0].text

    def test_dlr_entries_generated(self):
        events = [_make_event("E1"), _make_event("E2")]
        claims = TruthStage().process(events).claims
        out = ReasoningStage().process(events, claims)
        assert len(out.dlr_entries) == 2
        assert "lane" in out.dlr_entries[0]


class TestDriftStage:
    def test_fp_spike(self):
        # Create 6 events for same signature with low confidence
        events = [
            _make_event(f"E{i}", sig_id=999, confidence=0.3)
            for i in range(6)
        ]
        claims = TruthStage().process(events).claims
        reasoning = ReasoningStage().process(events, claims).results
        out = DriftStage(fp_spike_threshold=5).process(events, claims, reasoning)
        fp_drifts = [d for d in out.detections if d.drift_type == JRMDriftType.FP_SPIKE]
        assert len(fp_drifts) == 1
        assert fp_drifts[0].fingerprint["signature_id"] == "999"

    def test_stale_logic_conflicting_revs(self):
        events = [
            _make_event("E1", sig_id=100, rev=5),
            _make_event("E2", sig_id=100, rev=7),
        ]
        claims = TruthStage().process(events).claims
        reasoning = ReasoningStage().process(events, claims).results
        out = DriftStage().process(events, claims, reasoning)
        stale = [d for d in out.detections if d.drift_type == JRMDriftType.STALE_LOGIC]
        assert len(stale) == 1

    def test_no_drift_on_clean_data(self):
        events = [_make_event("E1", sig_id=100, confidence=0.9)]
        claims = TruthStage().process(events).claims
        reasoning = ReasoningStage().process(events, claims).results
        out = DriftStage(fp_spike_threshold=10).process(events, claims, reasoning)
        assert len(out.detections) == 0

    def test_ds_entries_generated(self):
        events = [_make_event(f"E{i}", sig_id=999, confidence=0.3) for i in range(6)]
        claims = TruthStage().process(events).claims
        reasoning = ReasoningStage().process(events, claims).results
        out = DriftStage(fp_spike_threshold=5).process(events, claims, reasoning)
        assert len(out.ds_entries) >= 1
        assert "driftType" in out.ds_entries[0]


class TestPatchStage:
    def test_rev_increment(self):
        dd = DriftDetection(
            drift_id="D-001", drift_type=JRMDriftType.FP_SPIKE,
            severity=Severity.MEDIUM, detected_at="2026-02-28T10:00:00Z",
            evidence_refs=["ref1"], fingerprint={"signature_id": "100"},
        )
        stage = PatchStage()
        out = stage.process([dd])
        assert len(out.patches) == 1
        assert out.patches[0].rev == 1
        assert out.patches[0].previous_rev == 0

    def test_sequential_rev_increment(self):
        dd1 = DriftDetection(
            drift_id="D-001", drift_type=JRMDriftType.FP_SPIKE,
            severity=Severity.MEDIUM, detected_at="2026-02-28T10:00:00Z",
            evidence_refs=[], fingerprint={"signature_id": "100"},
        )
        dd2 = DriftDetection(
            drift_id="D-002", drift_type=JRMDriftType.STALE_LOGIC,
            severity=Severity.MEDIUM, detected_at="2026-02-28T10:01:00Z",
            evidence_refs=[], fingerprint={"signature_id": "100"},
        )
        stage = PatchStage()
        out1 = stage.process([dd1])
        out2 = stage.process([dd2])
        assert out1.patches[0].rev == 1
        assert out2.patches[0].rev == 2
        assert out2.patches[0].supersedes == out1.patches[0].patch_id

    def test_lineage_preserved(self):
        dd1 = DriftDetection(
            drift_id="D-001", drift_type=JRMDriftType.FP_SPIKE,
            severity=Severity.MEDIUM, detected_at="2026-02-28T10:00:00Z",
            evidence_refs=[], fingerprint={"signature_id": "100"},
        )
        dd2 = DriftDetection(
            drift_id="D-002", drift_type=JRMDriftType.FP_SPIKE,
            severity=Severity.MEDIUM, detected_at="2026-02-28T10:01:00Z",
            evidence_refs=[], fingerprint={"signature_id": "100"},
        )
        stage = PatchStage()
        out1 = stage.process([dd1])
        out2 = stage.process([dd2])
        # Second patch lineage should include first patch
        assert out1.patches[0].patch_id in out2.patches[0].lineage


class TestMemoryGraphStage:
    def test_nodes_created(self):
        events = [_make_event("E1")]
        claims = [Claim(
            claim_id="C1", statement="test", confidence=0.9,
            evidence_refs=["ref"], source_events=["E1"],
            timestamp="2026-02-28T10:00:00Z",
        )]
        stage = MemoryGraphStage()
        out = stage.process(events, claims, [], [])
        assert len(out.mg_delta["nodesAdded"]) >= 2  # event + claim
        assert len(out.mg_delta["edgesAdded"]) >= 1  # evidence_of

    def test_canon_postures(self):
        claims = [Claim(
            claim_id="C1", statement="test", confidence=0.9,
            evidence_refs=[], source_events=["E1"],
            timestamp="2026-02-28T10:00:00Z",
        )]
        stage = MemoryGraphStage()
        out = stage.process([], claims, [], [])
        assert "entries" in out.canon_postures
        assert "C1" in out.canon_postures["entries"]


class TestPipelineRunner:
    def test_end_to_end(self):
        events = [
            _make_event(f"E{i}", sig_id=100, confidence=0.3)
            for i in range(6)
        ]
        runner = PipelineRunner(environment_id="test", fp_spike_threshold=5)
        result = runner.run(events)
        assert result.events_processed == 6
        assert len(result.claims) >= 1
        assert len(result.reasoning_results) == 6
        assert len(result.drift_detections) >= 1
        assert len(result.patches) >= 1
        assert result.mg_deltas.get("nodesAdded")
        assert result.errors == []

    def test_empty_events(self):
        runner = PipelineRunner(environment_id="test")
        result = runner.run([])
        assert result.events_processed == 0
        assert result.claims == []

    def test_window_bounds(self):
        events = [
            _make_event("E1", timestamp="2026-02-28T10:00:00Z"),
            _make_event("E2", timestamp="2026-02-28T10:05:00Z"),
        ]
        # Different sigs to avoid FP spike with 2 events
        events[0].metadata["signature_id"] = 100
        events[1].metadata["signature_id"] = 200
        runner = PipelineRunner(environment_id="test")
        result = runner.run(events)
        assert result.window_start == "2026-02-28T10:00:00Z"
        assert result.window_end == "2026-02-28T10:05:00Z"
