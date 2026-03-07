"""Dependency Map -- walk memory graph to map authority dependencies.

Provides graph traversal primitives used by the blast radius simulator.
Operates on MemoryGraph's internal _nodes and _edges.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set


# Edge kinds that propagate authority impact
_AUTHORITY_EDGE_KINDS = frozenset({
    "delegated_to",
    "can_act_on",
    "decides_claim",
    "claim_depends_on",
    "produced",
    "triggered",
    "resolved_by",
    "als_authorizes",
    "caused",
    "audited_as",
})

# Map NodeKind values to dependency bucket names
_KIND_TO_BUCKET = {
    "episode": "episodes",
    "action": "episodes",  # actions roll up to episodes
    "drift": "patches",    # drift is part of patch lifecycle
    "patch": "patches",
    "claim": "claims",
    "canon_entry": "canon_entries",
    "governance_artifact": "governance_artifacts",
    "audit_record": "audit_records",
    "policy_evaluation": "governance_artifacts",
    "authority_slice": "governance_artifacts",
}


def walk_authority_dependencies(
    target_id: str,
    memory_graph: Any,
    max_depth: int = 10,
) -> Dict[str, List[str]]:
    """Walk memory graph to map all downstream dependencies (AUTH-F19).

    BFS from target_id following authority-relevant edge kinds.

    Args:
        target_id: Starting node ID.
        memory_graph: MemoryGraph instance (or None for graceful no-op).
        max_depth: Maximum traversal depth.

    Returns:
        Dict bucketed by entity kind:
        {"actors", "claims", "episodes", "canon_entries", "patches",
         "governance_artifacts", "audit_records"}
    """
    result: Dict[str, List[str]] = {
        "actors": [],
        "claims": [],
        "episodes": [],
        "canon_entries": [],
        "patches": [],
        "governance_artifacts": [],
        "audit_records": [],
    }

    if memory_graph is None:
        return result

    nodes = getattr(memory_graph, "_nodes", {})
    edges = getattr(memory_graph, "_edges", [])

    if target_id not in nodes:
        return result

    # Build adjacency list for forward traversal
    adj: Dict[str, List[str]] = {}
    for edge in edges:
        kind = edge.kind if hasattr(edge, "kind") else edge.get("kind", "")
        kind_val = kind.value if hasattr(kind, "value") else str(kind)
        if kind_val not in _AUTHORITY_EDGE_KINDS:
            continue
        src = edge.source_id if hasattr(edge, "source_id") else edge.get("source_id", "")
        tgt = edge.target_id if hasattr(edge, "target_id") else edge.get("target_id", "")
        adj.setdefault(src, []).append(tgt)

    # BFS
    visited: Set[str] = {target_id}
    queue: deque = deque([(target_id, 0)])

    while queue:
        node_id, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for neighbor in adj.get(node_id, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)

            node = nodes.get(neighbor)
            if node is not None:
                kind = node.kind if hasattr(node, "kind") else node.get("kind", "")
                kind_val = kind.value if hasattr(kind, "value") else str(kind)
                bucket = _KIND_TO_BUCKET.get(kind_val)
                if bucket and bucket in result:
                    result[bucket].append(neighbor)

            queue.append((neighbor, depth + 1))

    # Check if any discovered nodes are actors (via delegated_to edges)
    for edge in edges:
        kind = edge.kind if hasattr(edge, "kind") else edge.get("kind", "")
        kind_val = kind.value if hasattr(kind, "value") else str(kind)
        if kind_val == "delegated_to":
            tgt = edge.target_id if hasattr(edge, "target_id") else edge.get("target_id", "")
            src = edge.source_id if hasattr(edge, "source_id") else edge.get("source_id", "")
            if src == target_id and tgt not in result["actors"]:
                result["actors"].append(tgt)
            elif src in visited and tgt not in result["actors"] and tgt not in visited:
                result["actors"].append(tgt)
                visited.add(tgt)

    return result


def find_authority_ancestors(
    target_id: str,
    memory_graph: Any,
) -> List[str]:
    """Walk backward to find all authority sources for a given entity.

    Reverse BFS following DELEGATED_TO and ALS_AUTHORIZES edges upstream.
    """
    if memory_graph is None:
        return []

    edges = getattr(memory_graph, "_edges", [])

    # Build reverse adjacency (target → source)
    rev_adj: Dict[str, List[str]] = {}
    for edge in edges:
        kind = edge.kind if hasattr(edge, "kind") else edge.get("kind", "")
        kind_val = kind.value if hasattr(kind, "value") else str(kind)
        if kind_val in ("delegated_to", "als_authorizes"):
            src = edge.source_id if hasattr(edge, "source_id") else edge.get("source_id", "")
            tgt = edge.target_id if hasattr(edge, "target_id") else edge.get("target_id", "")
            rev_adj.setdefault(tgt, []).append(src)

    ancestors: List[str] = []
    visited: Set[str] = {target_id}
    queue: deque = deque([target_id])

    while queue:
        node_id = queue.popleft()
        for parent in rev_adj.get(node_id, []):
            if parent not in visited:
                visited.add(parent)
                ancestors.append(parent)
                queue.append(parent)

    return ancestors


def count_affected_by_kind(
    dependencies: Dict[str, List[str]],
) -> Dict[str, int]:
    """Count dependencies by bucket kind."""
    return {k: len(v) for k, v in dependencies.items()}
