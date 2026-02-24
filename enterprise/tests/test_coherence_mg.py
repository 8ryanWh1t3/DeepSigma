"""Unit tests for core.mg — Memory Graph node/edge creation."""
import json
from core.mg import MemoryGraph


def _episode(episode_id="ep-1", decision_type="AccountQuarantine"):
    """Minimal episode for MG tests."""
    return {
        "episodeId": episode_id,
        "decisionType": decision_type,
        "actions": [
            {
                "type": "quarantine",
                "blastRadiusTier": "account",
                "idempotencyKey": f"ik-{episode_id}",
                "targetRefs": ["acc-001"],
            }
        ],
        "context": {"evidenceRefs": ["evidence-ref-001"]},
        "outcome": {"code": "success"},
        "degrade": {"step": "none"},
        "sealedAt": "2026-02-12T12:00:00Z",
        "seal": {"sealHash": "sha256:abc123"},
    }


def _drift_event(drift_id="drift-001", episode_id="ep-1", drift_type="freshness",
                 severity="yellow", fp_key="AQ:freshness:geo"):
    return {
        "driftId": drift_id,
        "episodeId": episode_id,
        "driftType": drift_type,
        "severity": severity,
        "detectedAt": "2026-02-12T15:00:00Z",
        "fingerprint": {"key": fp_key},
        "recommendedPatchType": "ttl_change",
    }


def _patch(patch_id="patch-001", drift_id="drift-001"):
    return {
        "patchId": patch_id,
        "driftId": drift_id,
        "patchType": "ttl_change",
        "appliedAt": "2026-02-12T16:00:00Z",
        "description": "Increase TTL from 30s to 60s",
        "changes": [{"field": "ttlMs", "old": 30000, "new": 60000}],
    }


class TestMemoryGraph:
    """MemoryGraph builds provenance nodes and edges."""

    def test_add_episode_creates_nodes(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        assert mg.node_count >= 1  # episode + action + evidence nodes

    def test_episode_node_kind(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        stats = mg.query("stats")
        assert stats["nodes_by_kind"].get("episode", 0) >= 1

    def test_action_node_created(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        stats = mg.query("stats")
        assert stats["nodes_by_kind"].get("action", 0) >= 1

    def test_evidence_node_created(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        stats = mg.query("stats")
        assert stats["nodes_by_kind"].get("evidence", 0) >= 1

    def test_produced_edge(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        stats = mg.query("stats")
        assert stats["edges_by_kind"].get("produced", 0) >= 1

    def test_evidence_of_edge(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        stats = mg.query("stats")
        assert stats["edges_by_kind"].get("evidence_of", 0) >= 1

    def test_add_drift(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        mg.add_drift(_drift_event())
        stats = mg.query("stats")
        assert stats["nodes_by_kind"].get("drift", 0) == 1
        assert stats["edges_by_kind"].get("triggered", 0) == 1

    def test_drift_recurrence_edge(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        mg.add_drift(_drift_event(drift_id="d1", fp_key="same-fp"))
        mg.add_drift(_drift_event(drift_id="d2", fp_key="same-fp"))
        stats = mg.query("stats")
        assert stats["edges_by_kind"].get("recurrence", 0) >= 1

    def test_add_patch(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        mg.add_drift(_drift_event())
        mg.add_patch(_patch())
        stats = mg.query("stats")
        assert stats["nodes_by_kind"].get("patch", 0) == 1
        assert stats["edges_by_kind"].get("resolved_by", 0) == 1

    def test_query_why(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        result = mg.query("why", episode_id="ep-1")
        assert result["episode_id"] == "ep-1"
        assert result["node"] is not None
        assert len(result["evidence_refs"]) >= 1
        assert len(result["actions"]) >= 1

    def test_query_drift(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        mg.add_drift(_drift_event())
        result = mg.query("drift", episode_id="ep-1")
        assert len(result["drift_events"]) == 1

    def test_query_patches(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        mg.add_drift(_drift_event())
        mg.add_patch(_patch())
        result = mg.query("patches", episode_id="ep-1")
        assert len(result["patches"]) == 1

    def test_query_stats(self):
        mg = MemoryGraph()
        result = mg.query("stats")
        assert result["total_nodes"] == 0
        assert result["total_edges"] == 0

    def test_query_unknown(self):
        mg = MemoryGraph()
        result = mg.query("unknown_question")
        assert "error" in result

    def test_to_json_valid(self):
        mg = MemoryGraph()
        mg.add_episode(_episode())
        raw = mg.to_json()
        data = json.loads(raw)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 1

    def test_node_edge_counts(self):
        mg = MemoryGraph()
        assert mg.node_count == 0
        assert mg.edge_count == 0
        mg.add_episode(_episode())
        assert mg.node_count > 0
        assert mg.edge_count > 0
