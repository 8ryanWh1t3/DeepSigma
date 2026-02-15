"""Memory Graph (MG) — provenance and recall graph.

The Memory Graph stores nodes (episodes, actions, drift fingerprints, patches,
claims) and edges (provenance, causation, recurrence, claim topology) to enable
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
    CLAIM = "claim"


class EdgeKind(str, Enum):
    """Types of edge in the Memory Graph."""

    PRODUCED = "produced"            # episode -> action
    TRIGGERED = "triggered"          # episode -> drift
    RESOLVED_BY = "resolved_by"      # drift -> patch
    EVIDENCE_OF = "evidence_of"      # evidence -> episode
    RECURRENCE = "recurrence"        # drift -> drift (same fingerprint)
    CAUSED = "caused"                # action -> episode (downstream)
    CLAIM_SUPPORTS = "claim_supports"        # claim -> claim
    CLAIM_CONTRADICTS = "claim_contradicts"  # claim <-> claim
    CLAIM_DEPENDS_ON = "claim_depends_on"    # claim -> claim
    CLAIM_SUPERSEDES = "claim_supersedes"    # claim -> claim
    CLAIM_EVIDENCE = "claim_evidence"        # claim -> evidence
    CLAIM_SOURCE = "claim_source"            # claim -> source node
    DECIDES_CLAIM = "decides_claim"          # episode -> claim


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
    """In-memory provenance graph built from episodes, drift events, and claims.

    Usage:
        mg = MemoryGraph()
        mg.add_episode(sealed_episode)
        mg.add_drift(drift_event)
        mg.add_patch(patch_record)
        mg.add_claim(claim_dict)
        results = mg.query("why", episode_id="ep-001")
        results = mg.query("claim", claim_id="CLAIM-2026-0001")
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

        logger.debug(
            "Added episode node %s with %d actions",
            ep_id, len(episode.get("actions", [])),
        )
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

        logger.debug(
            "Added drift node %s (type=%s)",
            drift_id, drift.get("driftType"),
        )
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

    def add_claim(self, claim: Dict[str, Any],
                  episode_id: Optional[str] = None) -> str:
        """Add an AtomicClaim as a node with full graph topology.

        Args:
            claim: An AtomicClaim dict (conforming to specs/claim.schema.json).
            episode_id: Optional episode to link via DECIDES_CLAIM edge.

        Returns:
            The claim_id of the added node.
        """
        claim_id = claim.get("claimId", "")
        self._add_node(GraphNode(
            node_id=claim_id,
            kind=NodeKind.CLAIM,
            label=claim.get("statement", ""),
            timestamp=claim.get("timestampCreated"),
            properties={
                "truth_type": claim.get("truthType"),
                "confidence": claim.get("confidence", {}).get("score"),
                "status_light": claim.get("statusLight"),
                "owner": claim.get("owner"),
                "version": claim.get("version"),
                "half_life_value": claim.get("halfLife", {}).get("value"),
                "half_life_unit": claim.get("halfLife", {}).get("unit"),
                "classification": claim.get("classificationTag"),
                "seal_hash": claim.get("seal", {}).get("hash"),
            },
        ))

        # Link to episode if provided
        if episode_id and episode_id in self._nodes:
            self._add_edge(GraphEdge(
                source_id=episode_id,
                target_id=claim_id,
                kind=EdgeKind.DECIDES_CLAIM,
            ))

        # Graph topology edges
        graph = claim.get("graph", {})
        for dep in graph.get("dependsOn", []):
            self._add_edge(GraphEdge(
                source_id=claim_id,
                target_id=dep,
                kind=EdgeKind.CLAIM_DEPENDS_ON,
            ))
        for contra in graph.get("contradicts", []):
            self._add_edge(GraphEdge(
                source_id=claim_id,
                target_id=contra,
                kind=EdgeKind.CLAIM_CONTRADICTS,
            ))
        supersedes = graph.get("supersedes")
        if supersedes:
            self._add_edge(GraphEdge(
                source_id=claim_id,
                target_id=supersedes,
                kind=EdgeKind.CLAIM_SUPERSEDES,
            ))
        for sup in graph.get("supports", []):
            self._add_edge(GraphEdge(
                source_id=claim_id,
                target_id=sup,
                kind=EdgeKind.CLAIM_SUPPORTS,
            ))

        # Evidence links
        for ev in claim.get("evidence", []):
            ev_ref = ev.get("ref", "")
            ev_id = f"evidence:{ev_ref}"
            self._add_node(GraphNode(
                node_id=ev_id,
                kind=NodeKind.EVIDENCE,
                label=ev.get("summary", ev_ref),
                properties={
                    "type": ev.get("type"),
                    "method": ev.get("method"),
                },
            ))
            self._add_edge(GraphEdge(
                source_id=claim_id,
                target_id=ev_id,
                kind=EdgeKind.CLAIM_EVIDENCE,
            ))

        logger.debug(
            "Added claim node %s (type=%s, confidence=%s)",
            claim_id, claim.get("truthType"),
            claim.get("confidence", {}).get("score"),
        )
        return claim_id

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, question: str, episode_id: str = "",
              claim_id: str = "") -> Dict[str, Any]:
        """Simple structured query.

        Supported *question* values:
          "why"     — return evidence and provenance for an episode
          "drift"   — return drift history for an episode
          "patches" — return patches linked to an episode's drift
          "claim"   — return claim details with graph neighbors
          "claims"  — return all claims linked to an episode
          "stats"   — return graph-wide statistics
        """
        if question == "why":
            return self._query_why(episode_id)
        if question == "drift":
            return self._query_drift(episode_id)
        if question == "patches":
            return self._query_patches(episode_id)
        if question == "claim":
            return self._query_claim(claim_id)
        if question == "claims":
            return self._query_claims(episode_id)
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

    def _query_claim(self, claim_id: str) -> Dict[str, Any]:
        """Full details for a single claim with all graph neighbors."""
        node = self._nodes.get(claim_id)
        if not node or node.kind != NodeKind.CLAIM:
            return {"claim_id": claim_id, "error": "Claim not found"}
        depends_on = [
            e.target_id for e in self._edges
            if e.source_id == claim_id and e.kind == EdgeKind.CLAIM_DEPENDS_ON
        ]
        contradicts = [
            e.target_id for e in self._edges
            if e.source_id == claim_id and e.kind == EdgeKind.CLAIM_CONTRADICTS
        ]
        supports = [
            e.target_id for e in self._edges
            if e.source_id == claim_id and e.kind == EdgeKind.CLAIM_SUPPORTS
        ]
        supersedes = [
            e.target_id for e in self._edges
            if e.source_id == claim_id and e.kind == EdgeKind.CLAIM_SUPERSEDES
        ]
        evidence = [
            e.target_id for e in self._edges
            if e.source_id == claim_id and e.kind == EdgeKind.CLAIM_EVIDENCE
        ]
        episodes = [
            e.source_id for e in self._edges
            if e.target_id == claim_id and e.kind == EdgeKind.DECIDES_CLAIM
        ]
        return {
            "claim_id": claim_id,
            "node": asdict(node),
            "depends_on": depends_on,
            "contradicts": contradicts,
            "supports": supports,
            "supersedes": supersedes,
            "evidence": evidence,
            "linked_episodes": episodes,
        }

    def _query_claims(self, episode_id: str) -> Dict[str, Any]:
        """All claims linked to an episode."""
        claim_ids = [
            e.target_id for e in self._edges
            if e.source_id == episode_id and e.kind == EdgeKind.DECIDES_CLAIM
        ]
        claim_nodes = [asdict(self._nodes[c]) for c in claim_ids if c in self._nodes]
        return {"episode_id": episode_id, "claims": claim_nodes}

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
