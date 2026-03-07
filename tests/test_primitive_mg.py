"""Tests for core.primitive_mg — Memory Graph primitive mapping."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.memory_graph import EdgeKind, MemoryGraph, NodeKind  # noqa: E402
from core.primitive_envelope import supersede_envelope, wrap_primitive  # noqa: E402
from core.primitive_mg import (  # noqa: E402
    PRIMITIVE_TO_NODE_KIND,
    ingest_envelope,
    ingest_loop_result,
)
from core.primitives import PrimitiveType  # noqa: E402


def _sample_envelope(ptype="claim"):
    return wrap_primitive(ptype, {"id": "X-001", "text": "test"}, "test-src")


# ── Mapping ────────────────────────────────────────────────────


class TestMapping:
    def test_maps_all_five_types(self):
        assert len(PRIMITIVE_TO_NODE_KIND) == 5
        for ptype in PrimitiveType:
            assert ptype in PRIMITIVE_TO_NODE_KIND

    def test_claim_maps_to_claim(self):
        assert PRIMITIVE_TO_NODE_KIND[PrimitiveType.CLAIM] == NodeKind.CLAIM

    def test_event_maps_to_episode(self):
        assert PRIMITIVE_TO_NODE_KIND[PrimitiveType.EVENT] == NodeKind.EPISODE

    def test_review_maps_to_review(self):
        assert PRIMITIVE_TO_NODE_KIND[PrimitiveType.REVIEW] == NodeKind.REVIEW

    def test_patch_maps_to_patch(self):
        assert PRIMITIVE_TO_NODE_KIND[PrimitiveType.PATCH] == NodeKind.PATCH

    def test_apply_maps_to_apply(self):
        assert PRIMITIVE_TO_NODE_KIND[PrimitiveType.APPLY] == NodeKind.APPLY


# ── ingest_envelope ────────────────────────────────────────────


class TestIngestEnvelope:
    def test_creates_node(self):
        mg = MemoryGraph()
        env = _sample_envelope("claim")
        node_id = ingest_envelope(mg, env)
        assert node_id == env.envelope_id
        assert mg.node_count == 1

    def test_node_kind_matches(self):
        mg = MemoryGraph()
        env = _sample_envelope("patch")
        ingest_envelope(mg, env)
        node = mg._nodes[env.envelope_id]
        assert node.kind == NodeKind.PATCH

    def test_node_properties(self):
        mg = MemoryGraph()
        env = _sample_envelope("review")
        ingest_envelope(mg, env)
        node = mg._nodes[env.envelope_id]
        assert node.properties["primitive_type"] == "review"
        assert node.properties["version"] == 1
        assert node.properties["source"] == "test-src"

    def test_supersede_creates_derived_from_edge(self):
        mg = MemoryGraph()
        old = _sample_envelope("claim")
        ingest_envelope(mg, old)
        new = supersede_envelope(old, {"id": "X-002"})
        ingest_envelope(mg, new)
        assert mg.node_count == 2
        assert mg.edge_count == 1
        edge = mg._edges[0]
        assert edge.kind == EdgeKind.DERIVED_FROM
        assert edge.source_id == old.envelope_id
        assert edge.target_id == new.envelope_id

    def test_no_edge_without_parent(self):
        mg = MemoryGraph()
        env = _sample_envelope("event")
        ingest_envelope(mg, env)
        assert mg.edge_count == 0


# ── ingest_loop_result ─────────────────────────────────────────


class TestIngestLoopResult:
    def test_ingests_all_steps(self):
        from core.coherence_loop import run_coherence_loop

        claim = {
            "id": "CLM-001",
            "text": "Test claim",
            "domain": "ops",
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "assumptions": ["All good"],
        }
        event = {
            "id": "EVT-001",
            "text": "Test event failed",
            "domain": "ops",
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "observed_state": {"status": "failed"},
            "metadata": {"violation": True},
        }
        result = run_coherence_loop(claim, event)
        mg = MemoryGraph()
        ingest_loop_result(mg, result)
        assert mg.node_count == len(result.steps)

    def test_preceded_by_edges(self):
        from core.coherence_loop import run_coherence_loop

        claim = {
            "id": "CLM-001",
            "text": "Test",
            "domain": "ops",
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        event = {
            "id": "EVT-001",
            "text": "Test event",
            "domain": "ops",
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "observed_state": {"status": "healthy"},
        }
        result = run_coherence_loop(claim, event)
        mg = MemoryGraph()
        ingest_loop_result(mg, result)
        preceded_edges = [e for e in mg._edges if e.kind == EdgeKind.PRECEDED_BY]
        assert len(preceded_edges) == len(result.steps) - 1
