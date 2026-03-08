"""ContextEnvelopeBuilder — assembles context from authority, DTE, policy, episode."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ContextEnvelope, _ctx_id, _now_iso


class ContextEnvelopeBuilder:
    """Fluent builder for ContextEnvelope.

    Usage::

        ctx_env = (ContextEnvelopeBuilder()
            .with_actor("agent-001", "agent")
            .with_domain("intelops")
            .with_dte(dte_spec)
            .with_episode("EP-abc123")
            .build())
    """

    def __init__(self) -> None:
        self._fields: Dict[str, Any] = {}

    # -- WHO --

    def with_actor(self, actor_id: str, actor_type: str = "agent") -> ContextEnvelopeBuilder:
        self._fields["actor_id"] = actor_id
        self._fields["actor_type"] = actor_type
        return self

    def with_authority(self, grant: Any) -> ContextEnvelopeBuilder:
        """Extract context from an AuthorityGrant dataclass."""
        if grant is None:
            return self
        self._fields["authority_id"] = getattr(grant, "authority_id", None)
        scope = getattr(grant, "scope", "")
        if scope:
            self._fields["scope"] = scope
        constraints = getattr(grant, "constraints", [])
        self._fields["policy_refs"] = [
            getattr(c, "constraint_id", "") for c in constraints
        ]
        return self

    def with_delegation_chain(self, chain: List[str]) -> ContextEnvelopeBuilder:
        self._fields["delegation_chain"] = chain
        return self

    # -- WHERE --

    def with_domain(self, domain: str) -> ContextEnvelopeBuilder:
        self._fields["domain"] = domain
        return self

    def with_blast_radius(self, tier: str) -> ContextEnvelopeBuilder:
        self._fields["blast_radius_tier"] = tier
        return self

    # -- WHEN --

    def with_dte(self, dte_spec: Dict[str, Any]) -> ContextEnvelopeBuilder:
        """Extract timing constraints from a DTE spec dict."""
        self._fields["dte_spec"] = dte_spec
        self._fields["deadline_ms"] = (
            dte_spec.get("deadlineMs") or dte_spec.get("deadline_ms")
        )
        budgets = (
            dte_spec.get("stageBudgetsMs")
            or dte_spec.get("stage_budgets_ms")
            or {}
        )
        self._fields["stage_budgets_ms"] = budgets
        freshness = dte_spec.get("freshness") or {}
        self._fields["freshness_ttl_ms"] = (
            freshness.get("defaultTtlMs") or freshness.get("default_ttl_ms")
        )
        limits = dte_spec.get("limits") or {}
        self._fields["max_hops"] = (
            limits.get("maxHops") or limits.get("max_hops")
        )
        self._fields["max_chain_depth"] = (
            limits.get("maxChainDepth") or limits.get("max_chain_depth")
        )
        return self

    # -- WHY --

    def with_goal(self, goal: str, rationale: str = "") -> ContextEnvelopeBuilder:
        self._fields["goal"] = goal
        self._fields["rationale"] = rationale
        return self

    def with_policy_pack(
        self, pack_id: str, policy_refs: Optional[List[str]] = None,
    ) -> ContextEnvelopeBuilder:
        self._fields["policy_pack_id"] = pack_id
        if policy_refs:
            existing = self._fields.get("policy_refs", [])
            self._fields["policy_refs"] = existing + policy_refs
        return self

    # -- CONSTRAINTS --

    def with_action_constraints(self, constraints: Dict[str, Any]) -> ContextEnvelopeBuilder:
        self._fields["action_constraints"] = constraints
        return self

    # -- SCOPE --

    def with_episode(self, episode_id: str) -> ContextEnvelopeBuilder:
        self._fields["episode_id"] = episode_id
        return self

    def with_cycle(self, cycle_id: str) -> ContextEnvelopeBuilder:
        self._fields["cycle_id"] = cycle_id
        return self

    def with_parent(self, parent_context_id: str) -> ContextEnvelopeBuilder:
        self._fields["parent_context_id"] = parent_context_id
        return self

    def with_related_entities(self, entity_ids: List[str]) -> ContextEnvelopeBuilder:
        self._fields["related_entity_ids"] = entity_ids
        return self

    def with_tags(self, tags: List[str]) -> ContextEnvelopeBuilder:
        self._fields["tags"] = tags
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> ContextEnvelopeBuilder:
        self._fields["metadata"] = metadata
        return self

    # -- Factory --

    @classmethod
    def from_ctx_dict(cls, ctx: Dict[str, Any]) -> ContextEnvelopeBuilder:
        """Bootstrap a builder from an existing fragmented ctx dict.

        Extracts known keys from the unstructured ctx dict that handlers
        currently receive, producing a typed ContextEnvelope.
        """
        builder = cls()
        if "actor_id" in ctx:
            builder.with_actor(ctx["actor_id"], ctx.get("actor_type", "system"))
        if "domain" in ctx:
            builder.with_domain(ctx["domain"])
        if "episode_id" in ctx:
            builder.with_episode(ctx["episode_id"])
        if "dte_spec" in ctx:
            builder.with_dte(ctx["dte_spec"])
        if "policy_pack_id" in ctx:
            builder.with_policy_pack(ctx["policy_pack_id"])
        if "goal" in ctx:
            builder.with_goal(ctx["goal"], ctx.get("rationale", ""))
        if "blast_radius_tier" in ctx:
            builder.with_blast_radius(ctx["blast_radius_tier"])
        return builder

    # -- Build --

    def build(self) -> ContextEnvelope:
        """Build the ContextEnvelope."""
        clean = {k: v for k, v in self._fields.items() if v is not None}
        return ContextEnvelope(
            context_id=_ctx_id(),
            created_at=_now_iso(),
            started_at=_now_iso(),
            **clean,
        )
