"""Memory Graph persistence backends.

Defines the abstract interface and a JSONL file-based MVP implementation.
The JSONL backend stores nodes in mg_nodes.jsonl and edges in mg_edges.jsonl.
"""
from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from coherence_ops.mg import EdgeKind, GraphEdge, GraphNode, NodeKind

logger = logging.getLogger(__name__)


class MGPersistenceBackend(ABC):
    """Abstract interface for Memory Graph persistence."""

    @abstractmethod
    def load(self) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        """Load all nodes and edges from storage."""
        ...

    @abstractmethod
    def save_node(self, node: GraphNode) -> None:
        """Persist a single node (append)."""
        ...

    @abstractmethod
    def save_edge(self, edge: GraphEdge) -> None:
        """Persist a single edge (append)."""
        ...

    @abstractmethod
    def save_all(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> None:
        """Bulk save all nodes and edges (full overwrite)."""
        ...


class JSONLBackend(MGPersistenceBackend):
    """JSONL file-based persistence backend.

    Thread-safe writes via a lock (consistent with exhaust_api.py pattern).
    """

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._nodes_file = directory / "mg_nodes.jsonl"
        self._edges_file = directory / "mg_edges.jsonl"
        self._lock = threading.Lock()

    def load(self) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        if self._nodes_file.exists():
            for line in self._nodes_file.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    node = GraphNode(
                        node_id=d["node_id"],
                        kind=NodeKind(d["kind"]),
                        label=d.get("label", ""),
                        timestamp=d.get("timestamp"),
                        properties=d.get("properties", {}),
                    )
                    nodes[node.node_id] = node
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        if self._edges_file.exists():
            for line in self._edges_file.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    edge = GraphEdge(
                        source_id=d["source_id"],
                        target_id=d["target_id"],
                        kind=EdgeKind(d["kind"]),
                        label=d.get("label", ""),
                        properties=d.get("properties", {}),
                    )
                    edges.append(edge)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return nodes, edges

    def save_node(self, node: GraphNode) -> None:
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            with open(self._nodes_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(node), default=str) + "\n")

    def save_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            with open(self._edges_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(edge), default=str) + "\n")

    def save_all(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> None:
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            with open(self._nodes_file, "w", encoding="utf-8") as f:
                for node in nodes.values():
                    f.write(json.dumps(asdict(node), default=str) + "\n")
            with open(self._edges_file, "w", encoding="utf-8") as f:
                for edge in edges:
                    f.write(json.dumps(asdict(edge), default=str) + "\n")


class InMemoryBackend(MGPersistenceBackend):
    """No-op backend for backward compatibility (default behavior)."""

    def load(self) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        return {}, []

    def save_node(self, node: GraphNode) -> None:
        pass

    def save_edge(self, edge: GraphEdge) -> None:
        pass

    def save_all(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> None:
        pass
