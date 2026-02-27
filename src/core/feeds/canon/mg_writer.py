"""Memory Graph writer — per-packet JSON graph from FEEDS events.

Builds a graph of nodes (one per event, typed by topic) and edges
(packet_contains, ds_detected_from, ce_resolves, als_authorizes).
Idempotent: same packet_id + same event hashes = same output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..envelope import compute_payload_hash


class MGWriter:
    """Build and write per-packet memory graph JSON files."""

    def build_graph(
        self, packet_id: str, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build a graph dict from a list of FEEDS event envelopes.

        Args:
            packet_id: The coherence packet ID.
            events: List of FEEDS event envelope dicts.

        Returns:
            A dict with ``packetId``, ``nodes``, and ``edges`` keys.
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Build packet node
        nodes.append({
            "nodeId": packet_id,
            "kind": "packet",
            "label": packet_id,
        })

        for event in events:
            event_id = event.get("eventId", "")
            topic = event.get("topic", "")
            payload = event.get("payload", {})

            # Node per event
            node = {
                "nodeId": event_id,
                "kind": topic,
                "label": _label_for_topic(topic, payload),
                "payloadHash": event.get("payloadHash", ""),
            }
            nodes.append(node)

            # Edge: packet_contains
            edges.append({
                "source": packet_id,
                "target": event_id,
                "kind": "packet_contains",
            })

            # Topic-specific edges
            if topic == "drift_signal":
                # ds_detected_from -> references
                for ref in payload.get("evidenceRefs", []):
                    edges.append({
                        "source": event_id,
                        "target": ref,
                        "kind": "ds_detected_from",
                    })

            elif topic == "canon_entry":
                # ce_resolves -> claim IDs
                for cid in payload.get("claimIds", []):
                    edges.append({
                        "source": event_id,
                        "target": cid,
                        "kind": "ce_resolves",
                    })

            elif topic == "authority_slice":
                # als_authorizes -> blessed claims
                for cid in payload.get("claimsBlessed", []):
                    edges.append({
                        "source": event_id,
                        "target": cid,
                        "kind": "als_authorizes",
                    })

        return {
            "packetId": packet_id,
            "nodes": nodes,
            "edges": edges,
        }

    def write_graph(
        self,
        packet_id: str,
        events: List[Dict[str, Any]],
        output_dir: str | Path,
    ) -> Path:
        """Build and write graph JSON to a file.

        Args:
            packet_id: The coherence packet ID.
            events: List of FEEDS event envelope dicts.
            output_dir: Directory to write the graph file into.

        Returns:
            Path to the written graph file.
        """
        graph = self.build_graph(packet_id, events)
        out = Path(output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)

        filepath = out / f"{packet_id}_graph.json"
        filepath.write_text(
            json.dumps(graph, indent=2), encoding="utf-8"
        )
        return filepath


def _label_for_topic(topic: str, payload: Dict[str, Any]) -> str:
    """Generate a human-readable label for a node based on its topic."""
    if topic == "truth_snapshot":
        return payload.get("snapshotId", topic)
    if topic == "authority_slice":
        return payload.get("sliceId", topic)
    if topic == "decision_lineage":
        return payload.get("dlrId", topic)
    if topic == "drift_signal":
        return payload.get("driftId", topic)
    if topic == "canon_entry":
        return payload.get("canonId", topic)
    if topic == "packet_index":
        return payload.get("packetId", topic)
    return topic
