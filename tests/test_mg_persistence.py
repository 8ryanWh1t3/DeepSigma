"""Tests for Memory Graph persistence backends."""

from coherence_ops.mg import EdgeKind, GraphEdge, GraphNode, MemoryGraph, NodeKind
from coherence_ops.mg_backends import InMemoryBackend, JSONLBackend


SAMPLE_EPISODE = {
    "episodeId": "ep-persist-001",
    "decisionType": "deploy",
    "sealedAt": "2026-02-18T00:00:00Z",
    "outcome": {"code": "success"},
    "degrade": {},
    "seal": {"sealHash": "abc123"},
    "actions": [
        {"idempotencyKey": "act-1", "type": "deploy", "blastRadiusTier": "low"},
    ],
    "context": {"evidenceRefs": ["doc-1"]},
}

SAMPLE_DRIFT = {
    "driftId": "drift-persist-001",
    "episodeId": "ep-persist-001",
    "driftType": "freshness",
    "severity": "yellow",
    "detectedAt": "2026-02-18T01:00:00Z",
    "fingerprint": {"key": "fp-abc"},
}


class TestJSONLBackendRoundTrip:
    def test_save_and_load_node(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        node = GraphNode(node_id="n1", kind=NodeKind.EPISODE, label="test")
        backend.save_node(node)

        nodes, edges = backend.load()
        assert "n1" in nodes
        assert nodes["n1"].kind == NodeKind.EPISODE
        assert nodes["n1"].label == "test"
        assert edges == []

    def test_save_and_load_edge(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        edge = GraphEdge(
            source_id="a", target_id="b", kind=EdgeKind.PRODUCED, label="test"
        )
        backend.save_edge(edge)

        nodes, edges = backend.load()
        assert nodes == {}
        assert len(edges) == 1
        assert edges[0].source_id == "a"
        assert edges[0].kind == EdgeKind.PRODUCED

    def test_multiple_nodes(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        backend.save_node(GraphNode(node_id="n1", kind=NodeKind.EPISODE))
        backend.save_node(GraphNode(node_id="n2", kind=NodeKind.DRIFT))
        backend.save_node(GraphNode(node_id="n3", kind=NodeKind.CLAIM))

        nodes, _ = backend.load()
        assert len(nodes) == 3

    def test_save_all_overwrites(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        backend.save_node(GraphNode(node_id="old", kind=NodeKind.EPISODE))

        new_nodes = {"new": GraphNode(node_id="new", kind=NodeKind.PATCH)}
        new_edges = [GraphEdge(source_id="a", target_id="b", kind=EdgeKind.CAUSED)]
        backend.save_all(new_nodes, new_edges)

        nodes, edges = backend.load()
        assert "old" not in nodes
        assert "new" in nodes
        assert len(edges) == 1

    def test_load_empty_directory(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        nodes, edges = backend.load()
        assert nodes == {}
        assert edges == []

    def test_properties_round_trip(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        node = GraphNode(
            node_id="n1",
            kind=NodeKind.DRIFT,
            properties={"severity": "red", "fingerprint_key": "fp-1"},
        )
        backend.save_node(node)
        nodes, _ = backend.load()
        assert nodes["n1"].properties["severity"] == "red"
        assert nodes["n1"].properties["fingerprint_key"] == "fp-1"


class TestMemoryGraphWithBackend:
    def test_backward_compat_no_backend(self):
        mg = MemoryGraph()
        mg.add_episode(SAMPLE_EPISODE)
        assert mg.node_count > 0

    def test_persists_across_instances(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        mg1 = MemoryGraph(backend=backend)
        mg1.add_episode(SAMPLE_EPISODE)
        node_count = mg1.node_count
        edge_count = mg1.edge_count

        # New instance loads from same backend
        mg2 = MemoryGraph(backend=JSONLBackend(tmp_path))
        assert mg2.node_count == node_count
        assert mg2.edge_count == edge_count

    def test_episode_and_drift_persist(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        mg1 = MemoryGraph(backend=backend)
        mg1.add_episode(SAMPLE_EPISODE)
        mg1.add_drift(SAMPLE_DRIFT)

        mg2 = MemoryGraph(backend=JSONLBackend(tmp_path))
        stats = mg2.query("stats")
        assert stats["nodes_by_kind"].get("episode", 0) >= 1
        assert stats["nodes_by_kind"].get("drift", 0) >= 1

    def test_query_works_after_reload(self, tmp_path):
        backend = JSONLBackend(tmp_path)
        mg1 = MemoryGraph(backend=backend)
        mg1.add_episode(SAMPLE_EPISODE)

        mg2 = MemoryGraph(backend=JSONLBackend(tmp_path))
        result = mg2.query("why", episode_id="ep-persist-001")
        assert result["episode_id"] == "ep-persist-001"
        assert result["node"] is not None


class TestInMemoryBackend:
    def test_noop(self):
        backend = InMemoryBackend()
        backend.save_node(GraphNode(node_id="x", kind=NodeKind.EPISODE))
        backend.save_edge(
            GraphEdge(source_id="a", target_id="b", kind=EdgeKind.PRODUCED)
        )
        nodes, edges = backend.load()
        assert nodes == {}
        assert edges == []
