"""Tests for ContextEnvelope — the ambient context wrapper for CERPA.

Validates that ContextEnvelope is NOT a primitive, and tests creation,
builder, propagation, snapshot, diff, validation, CERPA integration,
and Memory Graph integration.
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from src.core.context.models import ContextDiff, ContextEnvelope, ContextSnapshot
from src.core.context.builder import ContextEnvelopeBuilder
from src.core.context.propagation import (
    compute_context_diff,
    fork_context,
    inherit_context,
    merge_context,
    snapshot_context,
)
from src.core.context.validators import validate_context_envelope


# ── Helpers ──────────────────────────────────────────────────────


def _minimal_envelope(**overrides: Any) -> ContextEnvelope:
    """Create a minimal valid ContextEnvelope for testing."""
    defaults: Dict[str, Any] = {
        "context_id": "CTX-aabbccdd0011",
        "created_at": "2026-03-07T00:00:00+00:00",
        "actor_id": "agent-001",
        "actor_type": "agent",
        "domain": "intelops",
    }
    defaults.update(overrides)
    return ContextEnvelope(**defaults)


def _sample_dte() -> Dict[str, Any]:
    return {
        "deadlineMs": 5000,
        "stageBudgetsMs": {"review": 2000, "patch": 1500},
        "freshness": {"defaultTtlMs": 3600000},
        "limits": {"maxHops": 4, "maxChainDepth": 8},
    }


# ═══════════════════════════════════════════════════════════════
# 1. TestContextEnvelopeCreation
# ═══════════════════════════════════════════════════════════════


class TestContextEnvelopeCreation:
    def test_defaults(self):
        env = _minimal_envelope()
        assert env.context_id == "CTX-aabbccdd0011"
        assert env.actor_id == "agent-001"
        assert env.blast_radius_tier == "small"
        assert env.delegation_chain == []
        assert env.policy_refs == []
        assert env.tags == []

    def test_context_id_format(self):
        env = _minimal_envelope()
        assert re.match(r"^CTX-[a-f0-9]{12}$", env.context_id)

    def test_to_dict_minimal(self):
        env = _minimal_envelope()
        d = env.to_dict()
        assert d["contextId"] == "CTX-aabbccdd0011"
        assert d["actorId"] == "agent-001"
        assert d["actorType"] == "agent"
        assert d["domain"] == "intelops"
        # Default blast_radius_tier "small" is omitted
        assert "blastRadiusTier" not in d

    def test_to_dict_with_all_fields(self):
        env = _minimal_envelope(
            blast_radius_tier="large",
            goal="test-goal",
            rationale="test-rationale",
            deadline_ms=5000,
            episode_id="EP-001",
            tags=["tag1"],
            metadata={"key": "val"},
        )
        d = env.to_dict()
        assert d["blastRadiusTier"] == "large"
        assert d["goal"] == "test-goal"
        assert d["deadlineMs"] == 5000
        assert d["episodeId"] == "EP-001"
        assert d["tags"] == ["tag1"]
        assert d["metadata"] == {"key": "val"}

    def test_to_dict_omits_empty_optionals(self):
        env = _minimal_envelope()
        d = env.to_dict()
        assert "deadlineMs" not in d
        assert "episodeId" not in d
        assert "policyPackId" not in d
        assert "parentContextId" not in d


# ═══════════════════════════════════════════════════════════════
# 2. TestContextEnvelopeBuilder
# ═══════════════════════════════════════════════════════════════


class TestContextEnvelopeBuilder:
    def test_with_actor(self):
        env = ContextEnvelopeBuilder().with_actor("a-1", "human").build()
        assert env.actor_id == "a-1"
        assert env.actor_type == "human"
        assert env.context_id.startswith("CTX-")

    def test_with_domain(self):
        env = ContextEnvelopeBuilder().with_domain("franops").build()
        assert env.domain == "franops"

    def test_with_dte(self):
        dte = _sample_dte()
        env = ContextEnvelopeBuilder().with_dte(dte).build()
        assert env.deadline_ms == 5000
        assert env.stage_budgets_ms == {"review": 2000, "patch": 1500}
        assert env.freshness_ttl_ms == 3600000
        assert env.max_hops == 4
        assert env.max_chain_depth == 8

    def test_with_authority_none(self):
        env = ContextEnvelopeBuilder().with_authority(None).build()
        assert env.authority_id is None

    def test_with_goal(self):
        env = (
            ContextEnvelopeBuilder()
            .with_goal("resolve drift", "confidence dropped")
            .build()
        )
        assert env.goal == "resolve drift"
        assert env.rationale == "confidence dropped"

    def test_with_policy_pack(self):
        env = (
            ContextEnvelopeBuilder()
            .with_policy_pack("PP-001", ["POL-A", "POL-B"])
            .build()
        )
        assert env.policy_pack_id == "PP-001"
        assert env.policy_refs == ["POL-A", "POL-B"]

    def test_with_policy_pack_appends(self):
        env = (
            ContextEnvelopeBuilder()
            .with_policy_pack("PP-001", ["POL-A"])
            .with_policy_pack("PP-001", ["POL-B"])
            .build()
        )
        assert env.policy_refs == ["POL-A", "POL-B"]

    def test_chaining(self):
        env = (
            ContextEnvelopeBuilder()
            .with_actor("agent-007", "agent")
            .with_domain("authorityops")
            .with_blast_radius("medium")
            .with_episode("EP-XYZ")
            .with_tags(["urgent"])
            .build()
        )
        assert env.actor_id == "agent-007"
        assert env.domain == "authorityops"
        assert env.blast_radius_tier == "medium"
        assert env.episode_id == "EP-XYZ"
        assert env.tags == ["urgent"]

    def test_from_ctx_dict(self):
        ctx = {
            "actor_id": "bot-3",
            "actor_type": "service",
            "domain": "reflectionops",
            "episode_id": "EP-999",
            "goal": "audit",
            "rationale": "scheduled",
            "blast_radius_tier": "tiny",
        }
        env = ContextEnvelopeBuilder.from_ctx_dict(ctx).build()
        assert env.actor_id == "bot-3"
        assert env.actor_type == "service"
        assert env.domain == "reflectionops"
        assert env.episode_id == "EP-999"
        assert env.goal == "audit"
        assert env.blast_radius_tier == "tiny"

    def test_from_ctx_dict_minimal(self):
        env = ContextEnvelopeBuilder.from_ctx_dict({}).build()
        assert env.context_id.startswith("CTX-")
        assert env.actor_id == ""

    def test_build_excludes_none_values(self):
        env = ContextEnvelopeBuilder().build()
        # deadline_ms should be None (not set), not passed as None
        assert env.deadline_ms is None


# ═══════════════════════════════════════════════════════════════
# 3. TestContextPropagation
# ═══════════════════════════════════════════════════════════════


class TestContextPropagation:
    def test_inherit_basic(self):
        parent = _minimal_envelope()
        child = inherit_context(parent)
        assert child.context_id != parent.context_id
        assert child.parent_context_id == parent.context_id
        assert child.actor_id == parent.actor_id
        assert child.domain == parent.domain

    def test_inherit_new_domain(self):
        parent = _minimal_envelope(domain="intelops")
        child = inherit_context(parent, new_domain="franops")
        assert child.domain == "franops"
        assert child.parent_context_id == parent.context_id

    def test_inherit_new_episode(self):
        parent = _minimal_envelope(episode_id="EP-001")
        child = inherit_context(parent, new_episode_id="EP-002")
        assert child.episode_id == "EP-002"

    def test_inherit_overrides(self):
        parent = _minimal_envelope()
        child = inherit_context(parent, overrides={"goal": "override-goal"})
        assert child.goal == "override-goal"

    def test_inherit_isolates_collections(self):
        parent = _minimal_envelope(tags=["a", "b"])
        child = inherit_context(parent)
        child.tags.append("c")
        assert "c" not in parent.tags

    def test_fork_creates_n_children(self):
        parent = _minimal_envelope()
        targets = [
            {"domain": "franops"},
            {"domain": "reflectionops"},
            {"domain": "authorityops"},
        ]
        children = fork_context(parent, targets)
        assert len(children) == 3
        domains = {c.domain for c in children}
        assert domains == {"franops", "reflectionops", "authorityops"}
        for c in children:
            assert c.parent_context_id == parent.context_id

    def test_merge_primary_wins_scalars(self):
        a = _minimal_envelope(domain="intelops", goal="goal-a")
        b = _minimal_envelope(
            context_id="CTX-222222222222",
            domain="franops",
            goal="goal-b",
        )
        merged = merge_context(a, b)
        assert merged.domain == "intelops"  # primary wins
        assert merged.goal == "goal-a"  # primary wins

    def test_merge_unions_collections(self):
        a = _minimal_envelope(tags=["x"], policy_refs=["P1"])
        b = _minimal_envelope(
            context_id="CTX-222222222222",
            tags=["y"],
            policy_refs=["P2"],
        )
        merged = merge_context(a, b)
        assert "x" in merged.tags
        assert "y" in merged.tags
        assert "P1" in merged.policy_refs
        assert "P2" in merged.policy_refs

    def test_merge_no_duplicates(self):
        a = _minimal_envelope(tags=["shared"])
        b = _minimal_envelope(context_id="CTX-222222222222", tags=["shared"])
        merged = merge_context(a, b)
        assert merged.tags.count("shared") == 1

    def test_merge_parent_is_primary(self):
        a = _minimal_envelope()
        b = _minimal_envelope(context_id="CTX-222222222222")
        merged = merge_context(a, b)
        assert merged.parent_context_id == a.context_id


# ═══════════════════════════════════════════════════════════════
# 4. TestContextSnapshot
# ═══════════════════════════════════════════════════════════════


class TestContextSnapshot:
    def test_snapshot_captures_data(self):
        env = _minimal_envelope()
        snap = snapshot_context(env, "cerpa_review")
        assert snap.context_id == env.context_id
        assert snap.trigger == "cerpa_review"
        assert snap.snapshot_id.startswith("SNAP-")
        assert snap.envelope_data["contextId"] == env.context_id

    def test_snapshot_to_dict(self):
        snap = ContextSnapshot(
            snapshot_id="SNAP-test123",
            context_id="CTX-aabbccdd0011",
            captured_at="2026-03-07T00:00:00+00:00",
            trigger="cascade",
            envelope_data={"contextId": "CTX-aabbccdd0011"},
        )
        d = snap.to_dict()
        assert d["snapshotId"] == "SNAP-test123"
        assert d["trigger"] == "cascade"


# ═══════════════════════════════════════════════════════════════
# 5. TestContextDiff
# ═══════════════════════════════════════════════════════════════


class TestContextDiff:
    def test_detects_changes(self):
        before = _minimal_envelope(domain="intelops")
        after = _minimal_envelope(
            context_id="CTX-222222222222",
            domain="franops",
        )
        diff = compute_context_diff(before, after)
        assert "domain" in diff.changed_fields
        assert diff.changed_fields["domain"]["from"] == "intelops"
        assert diff.changed_fields["domain"]["to"] == "franops"

    def test_detects_additions(self):
        before = _minimal_envelope()
        after = _minimal_envelope(
            context_id="CTX-222222222222",
            goal="new-goal",
        )
        diff = compute_context_diff(before, after)
        assert "goal" in diff.added_fields

    def test_detects_removals(self):
        before = _minimal_envelope(goal="old-goal")
        after = _minimal_envelope(context_id="CTX-222222222222")
        diff = compute_context_diff(before, after)
        assert "goal" in diff.removed_fields

    def test_no_changes(self):
        env = _minimal_envelope()
        diff = compute_context_diff(env, env)
        assert diff.changed_fields == {}
        assert diff.added_fields == []
        assert diff.removed_fields == []

    def test_diff_to_dict(self):
        diff = ContextDiff(
            diff_id="DIFF-test",
            from_context_id="CTX-111",
            to_context_id="CTX-222",
            changed_fields={"domain": {"from": "a", "to": "b"}},
            added_fields=["goal"],
            removed_fields=[],
        )
        d = diff.to_dict()
        assert d["diffId"] == "DIFF-test"
        assert d["changedFields"]["domain"]["to"] == "b"


# ═══════════════════════════════════════════════════════════════
# 6. TestContextValidation
# ═══════════════════════════════════════════════════════════════


class TestContextValidation:
    def test_valid_passes(self):
        env = _minimal_envelope()
        errors = validate_context_envelope(env)
        assert errors == []

    def test_invalid_context_id(self):
        env = _minimal_envelope(context_id="BAD-id")
        errors = validate_context_envelope(env)
        assert any("context_id" in e for e in errors)

    def test_invalid_blast_radius(self):
        env = _minimal_envelope(blast_radius_tier="huge")
        errors = validate_context_envelope(env)
        assert any("blast_radius_tier" in e for e in errors)

    def test_invalid_actor_type(self):
        env = _minimal_envelope(actor_type="robot")
        errors = validate_context_envelope(env)
        assert any("actor_type" in e for e in errors)

    def test_negative_deadline(self):
        env = _minimal_envelope(deadline_ms=-1)
        errors = validate_context_envelope(env)
        assert any("deadline_ms" in e for e in errors)

    def test_zero_deadline(self):
        env = _minimal_envelope(deadline_ms=0)
        errors = validate_context_envelope(env)
        assert any("deadline_ms" in e for e in errors)

    def test_negative_freshness_ttl(self):
        env = _minimal_envelope(freshness_ttl_ms=-100)
        errors = validate_context_envelope(env)
        assert any("freshness_ttl_ms" in e for e in errors)

    def test_negative_max_hops(self):
        env = _minimal_envelope(max_hops=-1)
        errors = validate_context_envelope(env)
        assert any("max_hops" in e for e in errors)


# ═══════════════════════════════════════════════════════════════
# 7. TestContextNotAPrimitive
# ═══════════════════════════════════════════════════════════════


class TestContextNotAPrimitive:
    def test_not_in_primitive_type(self):
        from src.core.primitives import PrimitiveType
        values = {pt.value for pt in PrimitiveType}
        assert "context" not in values
        assert "context_envelope" not in values

    def test_no_primitive_type_field(self):
        env = _minimal_envelope()
        assert not hasattr(env, "primitive_type")

    def test_primitive_type_count_is_five(self):
        from src.core.primitives import PrimitiveType
        assert len(PrimitiveType) == 5


# ═══════════════════════════════════════════════════════════════
# 8. TestCerpaCycleContext
# ═══════════════════════════════════════════════════════════════


class TestCerpaCycleContext:
    def _make_cycle(self, context=None):
        from src.core.cerpa.models import CerpaCycle, Claim, Event, Review
        claim = Claim(
            id="C-1", text="test claim", domain="test",
            source="test", timestamp="2026-01-01T00:00:00Z",
        )
        event = Event(
            id="E-1", text="test event", domain="test",
            source="test", timestamp="2026-01-01T00:00:00Z",
        )
        review = Review(
            id="R-1", claim_id="C-1", event_id="E-1",
            domain="test", timestamp="2026-01-01T00:00:00Z",
            verdict="aligned", rationale="ok", drift_detected=False,
        )
        kwargs = {
            "cycle_id": "CYCLE-test",
            "domain": "test",
            "claim": claim,
            "event": event,
            "review": review,
        }
        if context is not None:
            kwargs["context"] = context
        return CerpaCycle(**kwargs)

    def test_cycle_without_context(self):
        cycle = self._make_cycle()
        assert cycle.context is None
        d = cycle.to_dict()
        assert "context" not in d

    def test_cycle_with_context(self):
        env = _minimal_envelope()
        cycle = self._make_cycle(context=env)
        assert cycle.context is env
        d = cycle.to_dict()
        assert "context" in d
        assert d["context"]["contextId"] == env.context_id


# ═══════════════════════════════════════════════════════════════
# 9. TestMemoryGraphContextSnapshot
# ═══════════════════════════════════════════════════════════════


class TestMemoryGraphContextSnapshot:
    def test_nodekind_exists(self):
        from src.core.memory_graph import NodeKind
        assert hasattr(NodeKind, "CONTEXT_SNAPSHOT")
        assert NodeKind.CONTEXT_SNAPSHOT.value == "context_snapshot"

    def test_edgekind_exists(self):
        from src.core.memory_graph import EdgeKind
        assert hasattr(EdgeKind, "CONTEXTUALIZED_BY")
        assert EdgeKind.CONTEXTUALIZED_BY.value == "contextualized_by"

    def test_add_context_snapshot(self):
        from src.core.memory_graph import EdgeKind, MemoryGraph, NodeKind
        mg = MemoryGraph()
        snap = snapshot_context(_minimal_envelope(), "test")

        # Add an episode node to link to
        mg.add_episode({
            "episode_id": "EP-001",
            "decision_type": "test",
            "actions": [],
        })

        node_id = mg.add_context_snapshot(snap, ["EP-001"])
        assert node_id == snap.snapshot_id
        assert mg.node_count >= 2  # episode + context_snapshot

        # Verify edge
        edges = [
            e for e in mg._edges
            if e.kind == EdgeKind.CONTEXTUALIZED_BY
        ]
        assert len(edges) == 1
        assert edges[0].source_id == "EP-001"
        assert edges[0].target_id == snap.snapshot_id
