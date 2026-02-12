"""Memory Graph (MG) — provenance and recall graph.

The Memory Graph stores nodes (episodes, actions, drift fingerprints,
patches) and edges (provenance, causation, recurrence) to enable
sub-60-second "why did we do this?" retrieval.

MG answers: "what happened before, why, and what changed as a result?"
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeKind(str, Enum):
    """Types of node in the Memory Graph."""

    EPISODE = "episode"
    ACTION = "action"
    DRIFT = "drift"
    PATCH = "patch"
    EVIDENCE = "evidence"


class EdgeKind(str, Enum):
    """Types of edge in the Memory Graph."""

    PRODUCED = "produced"          # episode -> action
    TRIGGERED = "triggered"        # episode -> drift
    RESOLVED_BY = "resolved_by"    # drift -> patch
    EVIDENCE_OF = "evidence_of"    # evidence -> episode
    RECURRENCE = "recurrence"      # drift -> drift (same fingerprint)
    CAUSED = "caused"              # action -> episode (downstream)


@dataclass
class GraphNode:
    """A node in the Memory Graph."""

    node_id: str
    kind: NodeKind
    label: str = ""
    timestamp: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed edge in the Memory Graph."""

    source_id: str
    target_id: str
    kind: EdgeKind
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


class MemoryGraph:
    """In-memory provenance graph built from episodes and drift events.

    Usage:
        mg = MemoryGraph()
        mg.add_episode(sealed_episode)
        mg.add_drift(drift_event)
        mg.add_patch(patch_record)
        results = mg.query("why", episode_id="ep-001")
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []

    @property
    def node_count(self) -> int:
        """Number of nodes."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges."""
        return len(self._edges)

    # ------------------------------------------------------------------
    # Ingest methods
    # ------------------------------------------------------------------

    def add_episode(self, episode: Dict[str, Any]) -> str:
        """Add a sealed episode as a node, plus action and evidence nodes."""
        ep_id = episode.get("episodeId", "")
        self._add_node(GraphNode(
            node_id=ep_id,
            kind=NodeKind.EPISODE,
            label=episode.get("decisionType", ""),
            timestamp=episode.get("sealedAt", episode.get("endedAt")),
            properties={
                "outcome": episode.get("outcome", {}).get("code"),
                "degrade_step": episode.get("degrade", {}).get("step"),
                "seal_hash": episode.get("seal", {}).get("sealHash"),
            },
        ))

        # Action nodes
        for idx, action in enumerate(episode.get("actions", [])):
            act_id = action.get("idempotencyKey", f"{ep_id}:action:{idx}")
            self._add_node(GraphNode(
                node_id=act_id,
                kind=NodeKind.ACTION,
                label=action.get("type", ""),
                properties={
                    "blast_radius": action.get("blastRadiusTier"),
                    "targets": action.get("targetRefs", []),
                },
            ))
            self._add_edge(GraphEdge(
                source_id=ep_id,
                target_id=act_id,
                kind=EdgeKind.PRODUCED,
            ))

        # Evidence nodes
        for ref in episode.get("context", {}).get("evidenceRefs", []):
            ev_id = f"evidence:{ref}"
            self._add_node(GraphNode(
                node_id=ev_id,
                kind=NodeKind.EVIDENCE,
                label=ref,
            ))
            self._add_edge(GraphEdge(
                source_id=ev_id,
                target_id=ep_id,
                kind=EdgeKind.EVIDENCE_OF,
            ))

        logger.debug("Added episode node %s with %d actions",
                     ep_id, len(episode.get("actions", [])))
        return ep_id

    def add_drift(self, drift: Dict[str, Any]) -> str:
        """Add a drift event as a node and link to its episode."""
        drift_id = drift.get("driftId", "")
        episode_id = drift.get("episodeId", "")
        fp = drift.get("fingerprint", {})

        self._add_node(GraphNode(
            node_id=drift_id,
            kind=NodeKind.DRIFT,
            label=drift.get("driftType", ""),
            timestamp=drift.get("detectedAt"),
            properties={
                "severity": drift.get("severity"),
                "fingerprint_key": fp.get("key"),
                "recommended_patch": drift.get("recommendedPatchType"),
            },
        ))

        if episode_id and episode_id in self._nodes:
            self._add_edge(GraphEdge(
                source_id=episode_id,
                target_id=drift_id,
                kind=EdgeKind.TRIGGERED,
            ))

        # Link recurrence (same fingerprint key)
        for nid, node in self._nodes.items():
            if (
                node.kind == NodeKind.DRIFT
                and nid != drift_id
                and node.properties.get("fingerprint_key") == fp.get("key")
            ):
                self._add_edge(GraphEdge(
                    source_id=nid,
                    target_id=drift_id,
                    kind=EdgeKind.RECURRENCE,
                ))

        logger.debug("Added drift node %s (type=%s)", drift_id, drift.get("driftType"))
        return drift_id

    def add_patch(self, patch: Dict[str, Any]) -> str:
        """Add a patch record and link to the drift it resolves."""
        patch_id = patch.get("patchId", "")
        drift_id = patch.get("driftId", "")

        self._add_node(GraphNode(
            node_id=patch_id,
            kind=NodeKind.PATCH,
            label=patch.get("patchType", ""),
            timestamp=patch.get("appliedAt"),
            properties={
                "description": patch.get("description"),
                "changes": patch.get("changes", []),
            },
        ))

        if drift_id and drift_id in self._nodes:
            self._add_edge(GraphEdge(
                source_id=drift_id,
                target_id=patch_id,
                kind=EdgeKind.RESOLVED_BY,
            ))

        logger.debug("Added patch node %s for drift %s", patch_id, drift_id)
        return patch_id

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, question: str, episode_id: str = "") -> Dict[str, Any]:
        """Simple structured query.

        Supported *question* values:
            "why"       — return evidence and provenance for an episode
            "drift"     — return drift history for an episode
            "patches"   — return patches linked to an episode's drift
            "stats"     — return graph-wide statistics
        """
        if question == "why":
            return self._query_why(episode_id)
        if question == "drift":
            return self._query_drift(episode_id)
        if question == "patches":
            return self._query_patches(episode_id)
        if question == "stats":
            return self._query_stats()
        return {"error": f"Unknown question: {question}"}

    def _query_why(self, episode_id: str) -> Dict[str, Any]:
        """Evidence and provenance for a specific episode."""
        evidence = [
            e.source_id for e in self._edges
            if e.target_id == episode_id and e.kind == EdgeKind.EVIDENCE_OF
        ]
        actions = [
            e.target_id for e in self._edges
            if e.source_id == episode_id and e.kind == EdgeKind.PRODUCED
        ]
        node = self._nodes.get(episode_id)
        return {
            "episode_id": episode_id,
            "node": asdict(node) if node else None,
            "evidence_refs": evidence,
            "actions": actions,
        }

    def _query_drift(self, episode_id: str) -> Dict[str, Any]:
        """Drift events linked to an episode."""
        drift_ids = [
            e.target_id for e in self._edges
            if e.source_id == episode_id and e.kind == EdgeKind.TRIGGERED
        ]
        drift_nodes = [asdict(self._nodes[d]) for d in drift_ids if d in self._nodes]
        return {"episode_id": episode_id, "drift_events": drift_nodes}

    def _query_patches(self, episode_id: str) -> Dict[str, Any]:
        """Patches linked to drift from an episode."""
        drift_ids = [
            e.target_id for e in self._edges
            if e.source_id == episode_id and e.kind == EdgeKind.TRIGGERED
        ]
        patch_ids = []
        for did in drift_ids:
            patch_ids.extend(
                e.target_id for e in self._edges
                if e.source_id == did and e.kind == EdgeKind.RESOLVED_BY
            )
        patch_nodes = [asdict(self._nodes[p]) for p in patch_ids if p in self._nodes]
        return {"episode_id": episode_id, "patches": patch_nodes}

    def _query_stats(self) -> Dict[str, Any]:
        """Graph-wide statistics."""
        kind_counts: Dict[str, int] = {}
        for node in self._nodes.values():
            k = node.kind.value
            kind_counts[k] = kind_counts.get(k, 0) + 1
        edge_counts: Dict[str, int] = {}
        for edge in self._edges:
            k = edge.kind.value
            edge_counts[k] = edge_counts.get(k, 0) + 1
        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "nodes_by_kind": kind_counts,
            "edges_by_kind": edge_counts,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise the full graph to JSON."""
        return json.dumps({
            "nodes": [asdict(n) for n in self._nodes.values()],
            "edges": [asdict(e) for e in self._edges],
        }, indent=indent)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_node(self, node: GraphNode) -> None:
        """Insert or update a node."""
        self._nodes[node.node_id] = node

    def _add_edge(self, edge: GraphEdge) -> None:
        """Append an edge (duplicates allowed)."""
        self._edges.append(edge)
