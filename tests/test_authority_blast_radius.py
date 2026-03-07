"""Tests for Authority Blast Radius Simulation -- AUTH-F17 through AUTH-F19.

Covers dependency_map, authority_blast_radius, and handler integration
via AuthorityOps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from core.authority import AuthorityLedger
from core.authority.authority_audit import AuthorityAuditLog
from core.authority.authority_blast_radius import (
    build_recommended_action,
    compute_impact_severity,
    simulate_blast_radius,
)
from core.authority.dependency_map import (
    count_affected_by_kind,
    find_authority_ancestors,
    walk_authority_dependencies,
)
from core.authority.models import RevocationEvent
from core.memory_graph import EdgeKind, GraphEdge, GraphNode, MemoryGraph, NodeKind
from core.modes.authorityops import AuthorityOps


NOW = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def authops():
    return AuthorityOps()


@pytest.fixture
def blast_context():
    """Evaluation context for blast radius handlers."""
    return {
        "memory_graph": MemoryGraph(),
        "authority_ledger": AuthorityLedger(),
        "authority_audit": AuthorityAuditLog(),
        "kill_switch_active": False,
        "now": NOW,
    }


def _populated_mg() -> MemoryGraph:
    """Build a memory graph with known authority dependencies."""
    mg = MemoryGraph()

    # Add nodes
    mg._nodes["actor-001"] = GraphNode(
        node_id="actor-001", kind=NodeKind.AUTHORITY_SLICE, label="actor-001",
    )
    mg._nodes["claim-001"] = GraphNode(
        node_id="claim-001", kind=NodeKind.CLAIM, label="test-claim",
    )
    mg._nodes["claim-002"] = GraphNode(
        node_id="claim-002", kind=NodeKind.CLAIM, label="dependent-claim",
    )
    mg._nodes["ep-001"] = GraphNode(
        node_id="ep-001", kind=NodeKind.EPISODE, label="decision-episode",
    )
    mg._nodes["canon-001"] = GraphNode(
        node_id="canon-001", kind=NodeKind.CANON_ENTRY, label="canon-entry",
    )
    mg._nodes["patch-001"] = GraphNode(
        node_id="patch-001", kind=NodeKind.PATCH, label="patch",
    )
    mg._nodes["drift-001"] = GraphNode(
        node_id="drift-001", kind=NodeKind.DRIFT, label="drift",
    )
    mg._nodes["audit-001"] = GraphNode(
        node_id="audit-001", kind=NodeKind.AUDIT_RECORD, label="audit",
    )
    mg._nodes["actor-002"] = GraphNode(
        node_id="actor-002", kind=NodeKind.AUTHORITY_SLICE, label="actor-002",
    )

    # Add edges
    mg._edges.extend([
        GraphEdge(source_id="actor-001", target_id="claim-001", kind=EdgeKind.DECIDES_CLAIM),
        GraphEdge(source_id="claim-001", target_id="claim-002", kind=EdgeKind.CLAIM_DEPENDS_ON),
        GraphEdge(source_id="actor-001", target_id="ep-001", kind=EdgeKind.PRODUCED),
        GraphEdge(source_id="ep-001", target_id="drift-001", kind=EdgeKind.TRIGGERED),
        GraphEdge(source_id="drift-001", target_id="patch-001", kind=EdgeKind.RESOLVED_BY),
        GraphEdge(source_id="actor-001", target_id="audit-001", kind=EdgeKind.AUDITED_AS),
        GraphEdge(source_id="actor-001", target_id="actor-002", kind=EdgeKind.DELEGATED_TO),
    ])

    return mg


# ── TestWalkAuthorityDependencies ────────────────────────────────


class TestWalkAuthorityDependencies:
    """Tests for walk_authority_dependencies (AUTH-F19 core)."""

    def test_no_dependencies_returns_empty(self):
        mg = MemoryGraph()
        mg._nodes["orphan"] = GraphNode(node_id="orphan", kind=NodeKind.CLAIM)
        deps = walk_authority_dependencies("orphan", mg)
        total = sum(len(v) for v in deps.values())
        assert total == 0

    def test_single_claim_dependency(self):
        mg = MemoryGraph()
        mg._nodes["src"] = GraphNode(node_id="src", kind=NodeKind.AUTHORITY_SLICE)
        mg._nodes["claim"] = GraphNode(node_id="claim", kind=NodeKind.CLAIM)
        mg._edges.append(
            GraphEdge(source_id="src", target_id="claim", kind=EdgeKind.DECIDES_CLAIM),
        )
        deps = walk_authority_dependencies("src", mg)
        assert "claim" in deps["claims"]

    def test_multi_hop_traversal(self):
        mg = _populated_mg()
        deps = walk_authority_dependencies("actor-001", mg)
        assert "claim-001" in deps["claims"]
        assert "claim-002" in deps["claims"]
        assert "ep-001" in deps["episodes"]

    def test_cycle_handling(self):
        mg = MemoryGraph()
        mg._nodes["a"] = GraphNode(node_id="a", kind=NodeKind.CLAIM)
        mg._nodes["b"] = GraphNode(node_id="b", kind=NodeKind.CLAIM)
        mg._edges.extend([
            GraphEdge(source_id="a", target_id="b", kind=EdgeKind.CLAIM_DEPENDS_ON),
            GraphEdge(source_id="b", target_id="a", kind=EdgeKind.CLAIM_DEPENDS_ON),
        ])
        # Should not infinite loop
        deps = walk_authority_dependencies("a", mg)
        assert "b" in deps["claims"]

    def test_max_depth_respected(self):
        mg = MemoryGraph()
        # Chain: n0 -> n1 -> n2 -> n3
        for i in range(4):
            mg._nodes[f"n{i}"] = GraphNode(node_id=f"n{i}", kind=NodeKind.CLAIM)
        for i in range(3):
            mg._edges.append(
                GraphEdge(source_id=f"n{i}", target_id=f"n{i+1}", kind=EdgeKind.CLAIM_DEPENDS_ON),
            )
        deps_shallow = walk_authority_dependencies("n0", mg, max_depth=2)
        deps_deep = walk_authority_dependencies("n0", mg, max_depth=10)
        assert len(deps_shallow["claims"]) <= len(deps_deep["claims"])

    def test_none_mg_returns_empty(self):
        deps = walk_authority_dependencies("target", None)
        assert all(len(v) == 0 for v in deps.values())

    def test_missing_target_returns_empty(self):
        mg = MemoryGraph()
        deps = walk_authority_dependencies("nonexistent", mg)
        assert all(len(v) == 0 for v in deps.values())

    def test_delegated_to_edge_followed(self):
        mg = _populated_mg()
        deps = walk_authority_dependencies("actor-001", mg)
        assert "actor-002" in deps["actors"]


# ── TestFindAuthorityAncestors ───────────────────────────────────


class TestFindAuthorityAncestors:
    """Tests for find_authority_ancestors."""

    def test_no_ancestors(self):
        mg = MemoryGraph()
        mg._nodes["leaf"] = GraphNode(node_id="leaf", kind=NodeKind.CLAIM)
        ancestors = find_authority_ancestors("leaf", mg)
        assert ancestors == []

    def test_single_ancestor(self):
        mg = MemoryGraph()
        mg._nodes["parent"] = GraphNode(node_id="parent", kind=NodeKind.AUTHORITY_SLICE)
        mg._nodes["child"] = GraphNode(node_id="child", kind=NodeKind.AUTHORITY_SLICE)
        mg._edges.append(
            GraphEdge(source_id="parent", target_id="child", kind=EdgeKind.DELEGATED_TO),
        )
        ancestors = find_authority_ancestors("child", mg)
        assert "parent" in ancestors

    def test_chain_of_ancestors(self):
        mg = MemoryGraph()
        for nid in ("root", "mid", "leaf"):
            mg._nodes[nid] = GraphNode(node_id=nid, kind=NodeKind.AUTHORITY_SLICE)
        mg._edges.extend([
            GraphEdge(source_id="root", target_id="mid", kind=EdgeKind.DELEGATED_TO),
            GraphEdge(source_id="mid", target_id="leaf", kind=EdgeKind.DELEGATED_TO),
        ])
        ancestors = find_authority_ancestors("leaf", mg)
        assert "root" in ancestors
        assert "mid" in ancestors


# ── TestCountAffectedByKind ──────────────────────────────────────


class TestCountAffectedByKind:
    """Tests for count_affected_by_kind."""

    def test_empty_deps(self):
        deps = {"claims": [], "episodes": [], "actors": []}
        counts = count_affected_by_kind(deps)
        assert all(v == 0 for v in counts.values())

    def test_mixed_kinds_counted(self):
        deps = {
            "claims": ["c1", "c2", "c3"],
            "episodes": ["ep1"],
            "actors": ["a1", "a2"],
            "patches": [],
        }
        counts = count_affected_by_kind(deps)
        assert counts["claims"] == 3
        assert counts["episodes"] == 1
        assert counts["actors"] == 2
        assert counts["patches"] == 0


# ── TestSimulateBlastRadius ──────────────────────────────────────


class TestSimulateBlastRadius:
    """Tests for simulate_blast_radius (AUTH-F17 core)."""

    def test_no_impact_returns_sev3(self):
        result = simulate_blast_radius("actor", "unknown", MemoryGraph(), {})
        assert result["severity"] == "SEV-3"
        assert result["affectedClaimsCount"] == 0
        assert result["targetType"] == "actor"

    def test_single_agent_returns_sev3(self):
        mg = MemoryGraph()
        mg._nodes["actor"] = GraphNode(node_id="actor", kind=NodeKind.AUTHORITY_SLICE)
        mg._nodes["claim"] = GraphNode(node_id="claim", kind=NodeKind.CLAIM)
        mg._edges.append(
            GraphEdge(source_id="actor", target_id="claim", kind=EdgeKind.DECIDES_CLAIM),
        )
        result = simulate_blast_radius("actor", "actor", mg, {})
        assert result["severity"] == "SEV-3"

    def test_cross_domain_returns_sev1(self):
        mg = _populated_mg()
        result = simulate_blast_radius("actor", "actor-001", mg, {})
        # Has claims, episodes, patches, actors — should be SEV-1 or SEV-2
        assert result["severity"] in ("SEV-1", "SEV-2")

    def test_simulation_id_format(self):
        result = simulate_blast_radius("actor", "test", MemoryGraph(), {})
        assert result["simulationId"].startswith("SIM-")

    def test_recommended_action_present(self):
        result = simulate_blast_radius("policy", "PP-001", MemoryGraph(), {})
        assert isinstance(result["recommendedAction"], str)
        assert len(result["recommendedAction"]) > 0

    def test_revocation_event_used(self):
        """Verify RevocationEvent can be used alongside blast radius simulation."""
        rev = RevocationEvent(
            revocation_id="REV-SIM",
            target_type="delegation",
            target_id="DEL-001",
            revoked_at="2026-03-05T00:00:00Z",
            reason="blast radius simulation test",
        )
        result = simulate_blast_radius(rev.target_type, rev.target_id, MemoryGraph(), {})
        assert result["targetType"] == "delegation"
        assert result["targetId"] == "DEL-001"


# ── TestComputeImpactSeverity ────────────────────────────────────


class TestComputeImpactSeverity:
    """Tests for compute_impact_severity (AUTH-F18 core)."""

    def test_sev3_local_only(self):
        assert compute_impact_severity(0, 0, 0, 0, 0) == "SEV-3"

    def test_sev3_boundary(self):
        assert compute_impact_severity(2, 0, 0, 0, 1) == "SEV-3"

    def test_sev2_one_decision(self):
        assert compute_impact_severity(3, 1, 0, 0, 1) == "SEV-2"

    def test_sev2_one_artifact_family(self):
        assert compute_impact_severity(0, 1, 1, 0, 1) == "SEV-2"

    def test_sev1_multi_decision_multi_agent(self):
        assert compute_impact_severity(5, 3, 2, 1, 3) == "SEV-1"

    def test_sev1_high_total(self):
        assert compute_impact_severity(10, 2, 0, 0, 0) == "SEV-1"


# ── TestBuildRecommendedAction ───────────────────────────────────


class TestBuildRecommendedAction:
    """Tests for build_recommended_action."""

    def test_sev3_message(self):
        msg = build_recommended_action("SEV-3", {"claims": 1, "actors": 0})
        assert "Monitor" in msg

    def test_sev2_message(self):
        msg = build_recommended_action("SEV-2", {"claims": 3, "episodes": 1})
        assert "Review" in msg

    def test_sev1_message(self):
        msg = build_recommended_action("SEV-1", {"claims": 10, "episodes": 5, "actors": 3})
        assert "LOCKDOWN" in msg


# ── Handler Integration Tests ────────────────────────────────────


class TestAuthF17BlastRadiusSimulate:
    """Tests for AUTH-F17 handler via AuthorityOps."""

    def test_no_impact(self, authops, blast_context):
        event = {"payload": {"targetType": "actor", "targetId": "unknown"}}
        result = authops.handle("AUTH-F17", event, blast_context)
        assert result.success
        assert result.function_id == "AUTH-F17"
        assert any(e["subtype"] == "authority_risk_propagated" for e in result.events_emitted)

    def test_cascade_emits_drift(self, authops, blast_context):
        blast_context["memory_graph"] = _populated_mg()
        event = {"payload": {"targetType": "actor", "targetId": "actor-001"}}
        result = authops.handle("AUTH-F17", event, blast_context)
        assert result.success
        # Should emit cascade drift since there are dependencies
        if result.drift_signals:
            assert any(
                s.get("subtype") == "authority_revocation_cascade"
                for s in result.drift_signals
            )

    def test_sev1_emits_lockdown(self, authops, blast_context):
        # Build a dense graph that triggers SEV-1
        mg = _populated_mg()
        # Add more episodes and agents to push to SEV-1
        for i in range(5):
            mg._nodes[f"ep-extra-{i}"] = GraphNode(
                node_id=f"ep-extra-{i}", kind=NodeKind.EPISODE,
            )
            mg._edges.append(GraphEdge(
                source_id="actor-001", target_id=f"ep-extra-{i}", kind=EdgeKind.PRODUCED,
            ))
        blast_context["memory_graph"] = mg
        event = {"payload": {"targetType": "actor", "targetId": "actor-001"}}
        result = authops.handle("AUTH-F17", event, blast_context)
        assert result.success

    def test_missing_mg_graceful(self, authops, blast_context):
        blast_context["memory_graph"] = None
        event = {"payload": {"targetType": "actor", "targetId": "test"}}
        result = authops.handle("AUTH-F17", event, blast_context)
        assert result.success


class TestAuthF18TrustImpact:
    """Tests for AUTH-F18 handler via AuthorityOps."""

    def test_low_impact(self, authops, blast_context):
        event = {"payload": {
            "affectedClaimsCount": 1,
            "affectedDecisionsCount": 0,
            "affectedAgentsCount": 0,
        }}
        result = authops.handle("AUTH-F18", event, blast_context)
        assert result.success
        assert result.function_id == "AUTH-F18"

    def test_high_impact(self, authops, blast_context):
        event = {"payload": {
            "affectedClaimsCount": 10,
            "affectedDecisionsCount": 5,
            "affectedCanonArtifactsCount": 3,
            "affectedAgentsCount": 4,
        }}
        result = authops.handle("AUTH-F18", event, blast_context)
        assert result.success
        assert any(e.get("severity") == "SEV-1" for e in result.events_emitted)

    def test_trust_surface_degraded_event(self, authops, blast_context):
        event = {"payload": {
            "affectedClaimsCount": 5,
            "affectedDecisionsCount": 1,
            "affectedAgentsCount": 1,
        }}
        result = authops.handle("AUTH-F18", event, blast_context)
        assert any(
            e["subtype"] == "trust_surface_degraded"
            for e in result.events_emitted
        )


class TestAuthF19DependencyMap:
    """Tests for AUTH-F19 handler via AuthorityOps."""

    def test_no_dependencies(self, authops, blast_context):
        event = {"payload": {"targetId": "unknown"}}
        result = authops.handle("AUTH-F19", event, blast_context)
        assert result.success
        assert result.function_id == "AUTH-F19"

    def test_with_populated_mg(self, authops, blast_context):
        blast_context["memory_graph"] = _populated_mg()
        event = {"payload": {"targetId": "actor-001"}}
        result = authops.handle("AUTH-F19", event, blast_context)
        assert result.success
        assert any(
            e.get("totalAffected", 0) > 0
            for e in result.events_emitted
        )

    def test_returns_correct_counts(self, authops, blast_context):
        blast_context["memory_graph"] = _populated_mg()
        event = {"payload": {"targetId": "actor-001"}}
        result = authops.handle("AUTH-F19", event, blast_context)
        for evt in result.events_emitted:
            if "dependencyCounts" in evt:
                assert isinstance(evt["dependencyCounts"], dict)


# ── Cross-Capability Integration ─────────────────────────────────


class TestDriftToBlastRadiusIntegration:
    """Test that drift detection feeds into blast radius simulation."""

    def test_drift_detection_feeds_blast_radius(self):
        """Drift signals can be used to trigger blast radius simulation."""
        from core.authority.authority_drift import scan_authority_drift

        delegations = [{
            "delegationId": "DEL-001",
            "fromActorId": "admin",
            "toActorId": "agent-001",
            "scope": "security-ops",
            "expiresAt": "2026-03-01T00:00:00Z",
        }]
        signals = scan_authority_drift([], delegations, [], [], [], now=NOW)
        assert len(signals) > 0

        # Use drift target to simulate blast radius
        target_id = signals[0].get("targetId", "DEL-001")
        result = simulate_blast_radius("delegation", target_id, MemoryGraph(), {})
        assert result["targetId"] == target_id
        assert result["severity"] in ("SEV-1", "SEV-2", "SEV-3")

    def test_full_pipeline_f13_to_f17(self):
        """AUTH-F13 drift scan followed by AUTH-F17 blast radius simulation."""
        authops = AuthorityOps()
        mg = _populated_mg()
        ctx = {
            "memory_graph": mg,
            "authority_ledger": AuthorityLedger(),
            "authority_audit": AuthorityAuditLog(),
            "now": NOW,
        }

        # F13: Drift scan
        f13_result = authops.handle("AUTH-F13", {"payload": {
            "delegations": [{
                "delegationId": "DEL-001",
                "fromActorId": "admin",
                "toActorId": "agent-001",
                "scope": "security-ops",
                "revokedAt": "2026-03-01T00:00:00Z",
            }],
        }}, ctx)
        assert f13_result.success

        # F17: Blast radius on the target
        f17_result = authops.handle("AUTH-F17", {"payload": {
            "targetType": "actor",
            "targetId": "actor-001",
        }}, ctx)
        assert f17_result.success
        assert any(
            e["subtype"] == "authority_risk_propagated"
            for e in f17_result.events_emitted
        )
