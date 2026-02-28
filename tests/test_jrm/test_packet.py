"""Tests for JRM-X packet builder."""

from __future__ import annotations

import json
import zipfile

from core.jrm.types import (
    Claim,
    DecisionLane,
    DriftDetection,
    EventType,
    JRMDriftType,
    JRMEvent,
    PatchRecord,
    PipelineResult,
    ReasoningResult,
    Severity,
    WhyBullet,
)
from core.jrm.packet.builder import RollingPacketBuilder
from core.jrm.packet.manifest import build_manifest, compute_file_hash
from core.jrm.packet.naming import generate_packet_name


REQUIRED_FILES = {
    "truth_snapshot.json",
    "authority_slice.json",
    "decision_lineage.jsonl",
    "drift_signal.jsonl",
    "memory_graph.json",
    "canon_entry.json",
    "manifest.json",
}


def _make_result(n_events=10, env="TEST") -> PipelineResult:
    return PipelineResult(
        environment_id=env,
        events_processed=n_events,
        window_start="2026-02-28T10:00:00Z",
        window_end="2026-02-28T10:10:00Z",
        claims=[Claim(
            claim_id="C1", statement="test", confidence=0.9,
            evidence_refs=["ref1"], source_events=["E1"],
            timestamp="2026-02-28T10:00:00Z",
        )],
        reasoning_results=[ReasoningResult(
            event_id="E1", lane=DecisionLane.NOTIFY,
            why_bullets=[WhyBullet("test", "ref1", 0.9)],
        )],
        drift_detections=[DriftDetection(
            drift_id="D1", drift_type=JRMDriftType.FP_SPIKE,
            severity=Severity.MEDIUM,
            detected_at="2026-02-28T10:05:00Z",
            evidence_refs=["ref1"],
            fingerprint={"signature_id": "100"},
        )],
        patches=[PatchRecord(
            patch_id="P1", drift_id="D1", rev=1, previous_rev=0,
            changes=[{"action": "adjust_threshold"}],
            applied_at="2026-02-28T10:06:00Z",
        )],
        mg_deltas={"nodesAdded": [{"nodeId": "E1", "kind": "evidence"}], "edgesAdded": []},
        canon_postures={"entries": {"C1": {"confidence": 0.9}}, "generatedAt": "2026-02-28T10:10:00Z"},
    )


class TestPacketNaming:
    def test_format(self):
        name = generate_packet_name("SOC_EAST", "2026-02-28T10:00:00Z", "2026-02-28T10:10:00Z", 1)
        assert name.startswith("JRM_X_PACKET_SOC_EAST_")
        assert "part01" in name

    def test_part_numbering(self):
        n1 = generate_packet_name("E", "2026-02-28T10:00:00Z", "2026-02-28T10:10:00Z", 1)
        n2 = generate_packet_name("E", "2026-02-28T10:00:00Z", "2026-02-28T10:10:00Z", 12)
        assert "part01" in n1
        assert "part12" in n2


class TestManifest:
    def test_file_hash(self):
        h = compute_file_hash(b"hello world")
        assert h.startswith("sha256:")
        assert len(h) == 71

    def test_build_manifest(self):
        files = {
            "truth_snapshot.json": b'{"test": true}',
            "authority_slice.json": b'{}',
            "decision_lineage.jsonl": b'',
            "drift_signal.jsonl": b'',
            "memory_graph.json": b'{}',
            "canon_entry.json": b'{}',
        }
        m = build_manifest("JRM_X_PACKET_TEST_20260228_20260228_part01",
                           files, "TEST", "2026-02-28T10:00:00Z",
                           "2026-02-28T10:10:00Z", 1, 100)
        assert m.packet_name.startswith("JRM_X_PACKET_")
        assert len(m.files) == 6
        for h in m.files.values():
            assert h.startswith("sha256:")


class TestRollingPacketBuilder:
    def test_produces_zip_with_7_files(self, tmp_jrm_output):
        builder = RollingPacketBuilder("TEST", tmp_jrm_output)
        builder.add(_make_result())
        path = builder.flush()
        assert path is not None
        assert path.suffix == ".zip"

        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            assert names == REQUIRED_FILES

    def test_manifest_hashes_match(self, tmp_jrm_output):
        builder = RollingPacketBuilder("TEST", tmp_jrm_output)
        builder.add(_make_result())
        path = builder.flush()

        with zipfile.ZipFile(path) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            for fname, expected in manifest["files"].items():
                actual = compute_file_hash(zf.read(fname))
                assert actual == expected, f"Hash mismatch for {fname}"

    def test_rolling_threshold(self, tmp_jrm_output):
        builder = RollingPacketBuilder("TEST", tmp_jrm_output, max_events=15)
        # Add 10, should not trigger
        p1 = builder.add(_make_result(n_events=10))
        assert p1 is None
        # Add 10 more, should trigger (total 20 >= 15)
        p2 = builder.add(_make_result(n_events=10))
        assert p2 is not None

    def test_part_numbering(self, tmp_jrm_output):
        builder = RollingPacketBuilder("TEST", tmp_jrm_output, max_events=50000)
        builder.add(_make_result(n_events=10))
        p1 = builder.flush()
        assert p1 is not None
        builder.add(_make_result(n_events=10))
        p2 = builder.flush()
        assert p2 is not None
        assert "part01" in p1.name
        assert "part02" in p2.name

    def test_flush_empty_returns_none(self, tmp_jrm_output):
        builder = RollingPacketBuilder("TEST", tmp_jrm_output)
        assert builder.flush() is None

    def test_packet_name_in_zip(self, tmp_jrm_output):
        builder = RollingPacketBuilder("SOC_EAST", tmp_jrm_output)
        builder.add(_make_result(env="SOC_EAST"))
        path = builder.flush()
        assert "SOC_EAST" in path.name
        assert path.name.startswith("JRM_X_PACKET_")
