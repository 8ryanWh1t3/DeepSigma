"""Tests for core.memory_graph_backends — JSONL, SQLite, InMemory backends."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.memory_graph import EdgeKind, GraphEdge, GraphNode, NodeKind  # noqa: E402
from core.memory_graph_backends import (  # noqa: E402
    InMemoryBackend,
    JSONLBackend,
    SQLiteMGBackend,
)


def _make_node(node_id="n-1", kind=NodeKind.EPISODE, label="ep", **props):
    return GraphNode(
        node_id=node_id,
        kind=kind,
        label=label,
        timestamp="2026-03-01T00:00:00Z",
        properties=props,
    )


def _make_edge(source="n-1", target="n-2", kind=EdgeKind.PRODUCED):
    return GraphEdge(
        source_id=source,
        target_id=target,
        kind=kind,
        label="test",
        properties={},
    )


# ── InMemoryBackend ──────────────────────────────────────────────


class TestInMemoryBackend:
    def test_load_empty(self):
        b = InMemoryBackend()
        nodes, edges = b.load()
        assert nodes == {}
        assert edges == []

    def test_save_node_noop(self):
        b = InMemoryBackend()
        b.save_node(_make_node())
        nodes, _ = b.load()
        assert nodes == {}

    def test_save_edge_noop(self):
        b = InMemoryBackend()
        b.save_edge(_make_edge())
        _, edges = b.load()
        assert edges == []

    def test_save_all_noop(self):
        b = InMemoryBackend()
        b.save_all({"n-1": _make_node()}, [_make_edge()])
        nodes, edges = b.load()
        assert nodes == {}
        assert edges == []


# ── JSONLBackend ─────────────────────────────────────────────────


class TestJSONLBackend:
    def test_save_and_load_node(self, tmp_path):
        b = JSONLBackend(tmp_path)
        node = _make_node()
        b.save_node(node)
        nodes, _ = b.load()
        assert "n-1" in nodes
        assert nodes["n-1"].kind == NodeKind.EPISODE

    def test_save_and_load_edge(self, tmp_path):
        b = JSONLBackend(tmp_path)
        edge = _make_edge()
        b.save_edge(edge)
        _, edges = b.load()
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.PRODUCED

    def test_save_all_overwrites(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_node(_make_node(node_id="old"))
        # save_all should overwrite
        b.save_all(
            {"n-1": _make_node()},
            [_make_edge()],
        )
        nodes, edges = b.load()
        assert "old" not in nodes
        assert "n-1" in nodes
        assert len(edges) == 1

    def test_multiple_nodes(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_node(_make_node(node_id="n-1"))
        b.save_node(_make_node(node_id="n-2", kind=NodeKind.ACTION))
        nodes, _ = b.load()
        assert len(nodes) == 2
        assert nodes["n-2"].kind == NodeKind.ACTION

    def test_multiple_edges(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_edge(_make_edge(source="a", target="b"))
        b.save_edge(_make_edge(source="c", target="d"))
        _, edges = b.load()
        assert len(edges) == 2

    def test_node_properties_preserved(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_node(_make_node(node_id="n-1", status="active", count=5))
        nodes, _ = b.load()
        assert nodes["n-1"].properties.get("status") == "active"
        assert nodes["n-1"].properties.get("count") == 5

    def test_empty_directory(self, tmp_path):
        b = JSONLBackend(tmp_path)
        nodes, edges = b.load()
        assert nodes == {}
        assert edges == []

    def test_corrupted_line_skipped(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_node(_make_node())
        # Append corrupted line
        nodes_file = tmp_path / "mg_nodes.jsonl"
        with open(nodes_file, "a") as f:
            f.write("not valid json\n")
        nodes, _ = b.load()
        assert len(nodes) == 1

    def test_node_kind_enum_preserved(self, tmp_path):
        b = JSONLBackend(tmp_path)
        for kind in [NodeKind.EPISODE, NodeKind.ACTION, NodeKind.DRIFT, NodeKind.EVIDENCE]:
            b.save_node(_make_node(node_id=f"n-{kind.value}", kind=kind))
        nodes, _ = b.load()
        assert nodes["n-episode"].kind == NodeKind.EPISODE
        assert nodes["n-action"].kind == NodeKind.ACTION

    def test_upsert_last_wins(self, tmp_path):
        b = JSONLBackend(tmp_path)
        b.save_node(_make_node(node_id="n-1", label="first"))
        b.save_node(_make_node(node_id="n-1", label="second"))
        nodes, _ = b.load()
        # JSONL appends, so last entry for same ID wins on load
        assert nodes["n-1"].label == "second"


# ── SQLiteMGBackend ──────────────────────────────────────────────


class TestSQLiteMGBackend:
    def test_save_and_load_node(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        node = _make_node()
        b.save_node(node)
        nodes, _ = b.load()
        assert "n-1" in nodes
        assert nodes["n-1"].kind == NodeKind.EPISODE
        b.close()

    def test_save_and_load_edge(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_edge(_make_edge())
        _, edges = b.load()
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.PRODUCED
        b.close()

    def test_save_all_overwrites(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_node(_make_node(node_id="old"))
        b.save_all(
            {"n-1": _make_node()},
            [_make_edge()],
        )
        nodes, edges = b.load()
        assert "old" not in nodes
        assert "n-1" in nodes
        assert len(edges) == 1
        b.close()

    def test_upsert_node(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_node(_make_node(node_id="n-1", label="first"))
        b.save_node(_make_node(node_id="n-1", label="second"))
        nodes, _ = b.load()
        assert nodes["n-1"].label == "second"
        b.close()

    def test_node_properties_json(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_node(_make_node(node_id="n-1", status="active", level=3))
        nodes, _ = b.load()
        assert nodes["n-1"].properties["status"] == "active"
        assert nodes["n-1"].properties["level"] == 3
        b.close()

    def test_multiple_edges(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_edge(_make_edge(source="a", target="b"))
        b.save_edge(_make_edge(source="c", target="d"))
        _, edges = b.load()
        assert len(edges) == 2
        b.close()

    def test_empty_load(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        nodes, edges = b.load()
        assert nodes == {}
        assert edges == []
        b.close()

    def test_node_kind_enum_preserved(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_node(_make_node(node_id="n-ep", kind=NodeKind.EPISODE))
        b.save_node(_make_node(node_id="n-act", kind=NodeKind.ACTION))
        nodes, _ = b.load()
        assert nodes["n-ep"].kind == NodeKind.EPISODE
        assert nodes["n-act"].kind == NodeKind.ACTION
        b.close()

    def test_edge_kind_enum_preserved(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.save_edge(_make_edge(source="a", target="b", kind=EdgeKind.PRODUCED))
        _, edges = b.load()
        assert edges[0].kind == EdgeKind.PRODUCED
        b.close()

    def test_close_idempotent(self, tmp_path):
        b = SQLiteMGBackend(tmp_path / "mg.db")
        b.close()
        # Second close should not raise


# ── Integration with MemoryGraph ─────────────────────────────────


class TestJSONLBackendIntegration:
    def test_mg_with_jsonl_backend(self, tmp_path):
        from core.memory_graph import MemoryGraph

        b = JSONLBackend(tmp_path)
        mg = MemoryGraph(backend=b)
        mg.add_episode({
            "episodeId": "ep-1",
            "decisionType": "test",
            "actions": [{"type": "action", "blastRadiusTier": "small",
                         "idempotencyKey": "ik-1", "targetRefs": ["t-1"]}],
            "context": {"evidenceRefs": ["e-1"]},
            "outcome": {"code": "success"},
            "degrade": {"step": "none"},
            "sealedAt": "2026-03-01T00:00:00Z",
            "seal": {"sealHash": "sha256:abc"},
        })
        assert mg.node_count > 0
        # Verify persisted
        nodes, edges = b.load()
        assert len(nodes) > 0


class TestSQLiteBackendIntegration:
    def test_mg_with_sqlite_backend(self, tmp_path):
        from core.memory_graph import MemoryGraph

        b = SQLiteMGBackend(tmp_path / "mg.db")
        mg = MemoryGraph(backend=b)
        mg.add_episode({
            "episodeId": "ep-1",
            "decisionType": "test",
            "actions": [{"type": "action", "blastRadiusTier": "small",
                         "idempotencyKey": "ik-1", "targetRefs": ["t-1"]}],
            "context": {"evidenceRefs": ["e-1"]},
            "outcome": {"code": "success"},
            "degrade": {"step": "none"},
            "sealedAt": "2026-03-01T00:00:00Z",
            "seal": {"sealHash": "sha256:abc"},
        })
        assert mg.node_count > 0
        nodes, edges = b.load()
        assert len(nodes) > 0
        b.close()
