"""Integration test — end-to-end JRM pipeline."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from core.jrm.adapters.suricata_eve import SuricataEVEAdapter
from core.jrm.adapters.copilot_agent import CopilotAgentAdapter
from core.jrm.pipeline.runner import PipelineRunner
from core.jrm.packet.builder import RollingPacketBuilder
from core.jrm.packet.manifest import compute_file_hash
from core.jrm.types import EventType

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "fixtures" / "jrm"

REQUIRED_DATA_FILES = {
    "truth_snapshot.json",
    "authority_slice.json",
    "decision_lineage.jsonl",
    "drift_signal.jsonl",
    "memory_graph.json",
    "canon_entry.json",
}


class TestEndToEnd:
    def test_suricata_full_pipeline(self, tmp_jrm_output):
        """Fixture file → adapter → pipeline → packet → validate."""
        adapter = SuricataEVEAdapter()
        lines = (FIXTURES_DIR / "suricata_eve_sample.jsonl").read_text().strip().splitlines()
        events = list(adapter.parse_stream(iter(lines), environment_id="TEST"))
        assert len(events) > 0

        runner = PipelineRunner(environment_id="TEST", fp_spike_threshold=3)
        result = runner.run(events)
        assert result.events_processed == len(events)
        assert result.errors == []
        assert len(result.claims) >= 1
        assert len(result.reasoning_results) == len(events)

        builder = RollingPacketBuilder("TEST", tmp_jrm_output)
        builder.add(result)
        packet_path = builder.flush()
        assert packet_path is not None

        # Validate packet structure
        with zipfile.ZipFile(packet_path) as zf:
            names = set(zf.namelist())
            assert REQUIRED_DATA_FILES.issubset(names)
            assert "manifest.json" in names

            # Manifest hashes match
            manifest = json.loads(zf.read("manifest.json"))
            for fname, expected_hash in manifest["files"].items():
                actual = compute_file_hash(zf.read(fname))
                assert actual == expected_hash

            # DLR has why bullets
            dlr_content = zf.read("decision_lineage.jsonl").decode("utf-8")
            dlr_lines = [json.loads(l) for l in dlr_content.strip().split("\n") if l.strip()]
            assert len(dlr_lines) > 0
            assert "whyBullets" in dlr_lines[0]
            assert len(dlr_lines[0]["whyBullets"]) >= 1

    def test_copilot_full_pipeline(self, tmp_jrm_output):
        adapter = CopilotAgentAdapter()
        lines = (FIXTURES_DIR / "copilot_agent_sample.jsonl").read_text().strip().splitlines()
        events = list(adapter.parse_stream(iter(lines), environment_id="TEST"))
        assert len(events) > 0

        runner = PipelineRunner(environment_id="TEST")
        result = runner.run(events)
        assert result.events_processed == len(events)
        assert result.errors == []

        builder = RollingPacketBuilder("TEST", tmp_jrm_output)
        builder.add(result)
        packet_path = builder.flush()
        assert packet_path is not None

        with zipfile.ZipFile(packet_path) as zf:
            names = set(zf.namelist())
            assert REQUIRED_DATA_FILES.issubset(names)

    def test_drift_detected_in_suricata_data(self, tmp_jrm_output):
        """Verify drift is detected in fixture data (conflicting revs → STALE_LOGIC)."""
        adapter = SuricataEVEAdapter()
        lines = (FIXTURES_DIR / "suricata_eve_sample.jsonl").read_text().strip().splitlines()
        events = list(adapter.parse_stream(iter(lines), environment_id="TEST"))

        runner = PipelineRunner(environment_id="TEST", fp_spike_threshold=3)
        result = runner.run(events)

        # Fixture has sig 2010935 with rev 6 AND rev 7 → STALE_LOGIC
        stale_drifts = [d for d in result.drift_detections
                        if d.drift_type.value == "STALE_LOGIC"]
        assert len(stale_drifts) >= 1

        # Each drift should produce a patch
        assert len(result.patches) >= 1
        assert result.patches[0].rev >= 1

    def test_malformed_lines_preserved(self):
        """Verify malformed lines become MALFORMED events."""
        adapter = SuricataEVEAdapter()
        lines = (FIXTURES_DIR / "suricata_eve_sample.jsonl").read_text().strip().splitlines()
        events = list(adapter.parse_stream(iter(lines)))
        malformed = [e for e in events if e.event_type == EventType.MALFORMED]
        assert len(malformed) >= 1
        assert malformed[0].raw_bytes != b""
