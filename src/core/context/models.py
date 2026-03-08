"""ContextEnvelope models — structured ambient context for CERPA operations.

The ContextEnvelope is NOT a primitive. It is a transport type that carries
who, when, where, why, constraints, and scope through the system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ctx_id() -> str:
    return f"CTX-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ContextEnvelope:
    """Structured ambient context for any CERPA operation.

    Carries six context dimensions:
      WHO:         actor identity, authority source, delegation chain
      WHEN:        timing, deadlines, DTE constraints
      WHERE:       domain, scope, blast radius
      WHY:         goal, rationale, policy references
      CONSTRAINTS: DTE limits, freshness rules, action constraints
      SCOPE:       episode, related entities, parent context
    """

    context_id: str
    created_at: str

    # -- WHO --
    actor_id: str = ""
    actor_type: str = ""                        # agent | human | system | service
    authority_id: Optional[str] = None
    delegation_chain: List[str] = field(default_factory=list)

    # -- WHEN --
    deadline_ms: Optional[int] = None
    stage_budgets_ms: Dict[str, int] = field(default_factory=dict)
    started_at: str = ""

    # -- WHERE --
    domain: str = ""
    scope: str = ""
    blast_radius_tier: str = "small"            # tiny | small | medium | large

    # -- WHY --
    goal: str = ""
    rationale: str = ""
    policy_refs: List[str] = field(default_factory=list)
    policy_pack_id: Optional[str] = None

    # -- CONSTRAINTS --
    dte_spec: Dict[str, Any] = field(default_factory=dict)
    freshness_ttl_ms: Optional[int] = None
    max_hops: Optional[int] = None
    max_chain_depth: Optional[int] = None
    action_constraints: Dict[str, Any] = field(default_factory=dict)

    # -- SCOPE --
    episode_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    related_entity_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # -- METADATA --
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to camelCase dict for transport/storage."""
        d: Dict[str, Any] = {
            "contextId": self.context_id,
            "createdAt": self.created_at,
        }
        if self.actor_id:
            d["actorId"] = self.actor_id
        if self.actor_type:
            d["actorType"] = self.actor_type
        if self.authority_id is not None:
            d["authorityId"] = self.authority_id
        if self.delegation_chain:
            d["delegationChain"] = self.delegation_chain
        if self.deadline_ms is not None:
            d["deadlineMs"] = self.deadline_ms
        if self.stage_budgets_ms:
            d["stageBudgetsMs"] = self.stage_budgets_ms
        if self.started_at:
            d["startedAt"] = self.started_at
        if self.domain:
            d["domain"] = self.domain
        if self.scope:
            d["scope"] = self.scope
        if self.blast_radius_tier and self.blast_radius_tier != "small":
            d["blastRadiusTier"] = self.blast_radius_tier
        if self.goal:
            d["goal"] = self.goal
        if self.rationale:
            d["rationale"] = self.rationale
        if self.policy_refs:
            d["policyRefs"] = self.policy_refs
        if self.policy_pack_id is not None:
            d["policyPackId"] = self.policy_pack_id
        if self.dte_spec:
            d["dteSpec"] = self.dte_spec
        if self.freshness_ttl_ms is not None:
            d["freshnessTtlMs"] = self.freshness_ttl_ms
        if self.max_hops is not None:
            d["maxHops"] = self.max_hops
        if self.max_chain_depth is not None:
            d["maxChainDepth"] = self.max_chain_depth
        if self.action_constraints:
            d["actionConstraints"] = self.action_constraints
        if self.episode_id is not None:
            d["episodeId"] = self.episode_id
        if self.cycle_id is not None:
            d["cycleId"] = self.cycle_id
        if self.parent_context_id is not None:
            d["parentContextId"] = self.parent_context_id
        if self.related_entity_ids:
            d["relatedEntityIds"] = self.related_entity_ids
        if self.tags:
            d["tags"] = self.tags
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class ContextSnapshot:
    """Immutable snapshot of a ContextEnvelope for Memory Graph storage."""

    snapshot_id: str
    context_id: str
    captured_at: str
    trigger: str                # e.g. "cerpa_review", "cascade_propagate"
    envelope_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshotId": self.snapshot_id,
            "contextId": self.context_id,
            "capturedAt": self.captured_at,
            "trigger": self.trigger,
            "envelopeData": self.envelope_data,
        }


@dataclass
class ContextDiff:
    """Diff between two ContextEnvelopes — tracks what changed."""

    diff_id: str
    from_context_id: str
    to_context_id: str
    changed_fields: Dict[str, Any] = field(default_factory=dict)
    added_fields: List[str] = field(default_factory=list)
    removed_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diffId": self.diff_id,
            "fromContextId": self.from_context_id,
            "toContextId": self.to_context_id,
            "changedFields": self.changed_fields,
            "addedFields": self.added_fields,
            "removedFields": self.removed_fields,
        }
