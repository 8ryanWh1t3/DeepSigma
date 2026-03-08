"""Context propagation — inherit, fork, merge, snapshot, diff."""

from __future__ import annotations

import copy
import uuid
from dataclasses import fields as dc_fields
from typing import Any, Dict, List, Optional, Sequence

from .models import ContextDiff, ContextEnvelope, ContextSnapshot, _ctx_id, _now_iso

# Fields that always get a fresh value on inherit / fork
_RESET_ON_INHERIT = {"context_id", "created_at", "started_at", "metadata"}

# Scalar fields (overridden by child; primary wins on merge)
_SCALAR_FIELDS = {
    "actor_id", "actor_type", "authority_id", "deadline_ms",
    "started_at", "domain", "scope", "blast_radius_tier",
    "goal", "rationale", "policy_pack_id", "freshness_ttl_ms",
    "max_hops", "max_chain_depth", "episode_id", "cycle_id",
}

# Collection fields (unioned on merge)
_COLLECTION_FIELDS = {
    "delegation_chain", "policy_refs", "related_entity_ids", "tags",
}


def inherit_context(
    parent: ContextEnvelope,
    *,
    new_domain: Optional[str] = None,
    new_episode_id: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> ContextEnvelope:
    """Create a child context from a parent.

    The child receives a new ID and links back to the parent via
    ``parent_context_id``.  Domain and episode can be overridden for
    cross-domain cascade propagation.
    """
    data: Dict[str, Any] = {}
    for f in dc_fields(parent):
        if f.name in _RESET_ON_INHERIT:
            continue
        val = getattr(parent, f.name)
        data[f.name] = copy.deepcopy(val) if isinstance(val, (list, dict)) else val

    data["context_id"] = _ctx_id()
    data["created_at"] = _now_iso()
    data["started_at"] = _now_iso()
    data["parent_context_id"] = parent.context_id
    data["metadata"] = {}

    if new_domain is not None:
        data["domain"] = new_domain
    if new_episode_id is not None:
        data["episode_id"] = new_episode_id
    if overrides:
        data.update(overrides)

    return ContextEnvelope(**data)


def fork_context(
    parent: ContextEnvelope,
    targets: Sequence[Dict[str, Any]],
) -> List[ContextEnvelope]:
    """Fork a parent context into N independent branches.

    Each target dict may override domain, episode_id, or other fields.

    Returns one child ContextEnvelope per target.
    """
    return [
        inherit_context(parent, overrides=target)
        for target in targets
    ]


def merge_context(
    primary: ContextEnvelope,
    *others: ContextEnvelope,
) -> ContextEnvelope:
    """Merge multiple contexts — primary wins scalars, collections union.

    Used when converging branches (e.g. multi-domain cascade results).
    """
    data: Dict[str, Any] = {}
    for f in dc_fields(primary):
        val = getattr(primary, f.name)
        data[f.name] = copy.deepcopy(val) if isinstance(val, (list, dict)) else val

    # Give merged context a new identity
    data["context_id"] = _ctx_id()
    data["created_at"] = _now_iso()
    data["started_at"] = _now_iso()
    data["parent_context_id"] = primary.context_id
    data["metadata"] = {}

    # Union collections from all others
    for other in others:
        for col_field in _COLLECTION_FIELDS:
            existing = data.get(col_field, [])
            incoming = getattr(other, col_field, [])
            merged = list(existing)
            for item in incoming:
                if item not in merged:
                    merged.append(item)
            data[col_field] = merged

        # Merge dict fields (stage_budgets_ms, action_constraints, dte_spec)
        for dict_field in ("stage_budgets_ms", "action_constraints"):
            existing = data.get(dict_field, {})
            incoming = getattr(other, dict_field, {})
            merged_dict = {**existing, **incoming}
            data[dict_field] = merged_dict

    return ContextEnvelope(**data)


def snapshot_context(
    envelope: ContextEnvelope,
    trigger: str,
) -> ContextSnapshot:
    """Capture an immutable snapshot for Memory Graph storage."""
    return ContextSnapshot(
        snapshot_id=f"SNAP-{uuid.uuid4().hex[:12]}",
        context_id=envelope.context_id,
        captured_at=_now_iso(),
        trigger=trigger,
        envelope_data=envelope.to_dict(),
    )


def compute_context_diff(
    before: ContextEnvelope,
    after: ContextEnvelope,
) -> ContextDiff:
    """Compute the diff between two ContextEnvelopes.

    Returns a ContextDiff listing changed, added, and removed fields.
    Ignores context_id, created_at, started_at (always differ).
    """
    ignore = {"context_id", "created_at", "started_at"}
    changed: Dict[str, Any] = {}
    added: List[str] = []
    removed: List[str] = []

    before_dict = before.to_dict()
    after_dict = after.to_dict()

    all_keys = set(before_dict.keys()) | set(after_dict.keys())
    for key in sorted(all_keys):
        if key in {"contextId", "createdAt", "startedAt"}:
            continue
        in_before = key in before_dict
        in_after = key in after_dict
        if in_before and in_after:
            if before_dict[key] != after_dict[key]:
                changed[key] = {"from": before_dict[key], "to": after_dict[key]}
        elif in_after and not in_before:
            added.append(key)
        elif in_before and not in_after:
            removed.append(key)

    return ContextDiff(
        diff_id=f"DIFF-{uuid.uuid4().hex[:12]}",
        from_context_id=before.context_id,
        to_context_id=after.context_id,
        changed_fields=changed,
        added_fields=added,
        removed_fields=removed,
    )
