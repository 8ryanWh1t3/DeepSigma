"""Tests for JRM Hub."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "enterprise" / "src"))

from deepsigma.jrm_ext.federation.hub import JRMHub
from deepsigma.jrm_ext.types import CrossEnvDriftType


class TestHub:
    def test_ingest_multiple_packets(self, make_packet):
        hub = JRMHub()
        p1 = make_packet(env="SOC_EAST")
        p2 = make_packet(env="SOC_WEST")
        hub.ingest([p1, p2])
        report = hub.produce_report()
        assert "SOC_EAST" in report["environments"]
        assert "SOC_WEST" in report["environments"]
        assert report["packetsIngested"] == 2

    def test_detect_version_skew(self, make_packet):
        """Different revs for same key across envs → VERSION_SKEW."""
        p1 = make_packet(
            env="SOC_EAST",
            canon_entries={"PATCH-abc": {"rev": 6, "previousRev": 5}},
        )
        p2 = make_packet(
            env="SOC_WEST",
            canon_entries={"PATCH-abc": {"rev": 8, "previousRev": 7}},
        )
        hub = JRMHub()
        hub.ingest([p1, p2])
        drifts = hub.detect_drift()
        skew = [d for d in drifts if d.drift_type == CrossEnvDriftType.VERSION_SKEW]
        assert len(skew) >= 1

    def test_detect_posture_divergence(self, make_packet):
        """Different confidence for same key → POSTURE_DIVERGENCE."""
        p1 = make_packet(
            env="SOC_EAST",
            canon_entries={"CLM-xyz": {"confidence": 0.95, "statement": "test"}},
        )
        p2 = make_packet(
            env="SOC_WEST",
            canon_entries={"CLM-xyz": {"confidence": 0.4, "statement": "test"}},
        )
        hub = JRMHub()
        hub.ingest([p1, p2])
        drifts = hub.detect_drift()
        diverge = [d for d in drifts if d.drift_type == CrossEnvDriftType.POSTURE_DIVERGENCE]
        assert len(diverge) >= 1

    def test_no_drift_on_single_env(self, make_packet):
        hub = JRMHub()
        hub.ingest([make_packet(env="SOC_EAST")])
        drifts = hub.detect_drift()
        assert len(drifts) == 0

    def test_merge_memory_graphs(self, make_packet):
        p1 = make_packet(
            env="A",
            mg_nodes=[{"nodeId": "N1", "kind": "evidence"}],
        )
        p2 = make_packet(
            env="B",
            mg_nodes=[{"nodeId": "N2", "kind": "claim"}],
        )
        hub = JRMHub()
        hub.ingest([p1, p2])
        mg = hub.merge_memory_graphs()
        assert len(mg["globalNodes"]) == 2
        assert "A" in mg["environments"]
        assert "B" in mg["environments"]
