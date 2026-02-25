"""Memory Graph persistence backends.

Defines the abstract interface and implementations for JSONL, SQLite, and
PostgreSQL. The JSONL backend stores nodes in mg_nodes.jsonl and edges in
mg_edges.jsonl. The SQL backends use a shared schema with JSON/JSONB columns.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from .mg import EdgeKind, GraphEdge, GraphNode, NodeKind

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


_SQLITE_MG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS mg_nodes (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    label TEXT DEFAULT '',
    timestamp TEXT,
    properties TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS mg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT DEFAULT '',
    properties TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
"""


class SQLiteMGBackend(MGPersistenceBackend):
    """SQLite-based Memory Graph persistence using stdlib sqlite3."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SQLITE_MG_SCHEMA)
        self._conn.commit()

    def load(self) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        for row in self._conn.execute(
            "SELECT node_id, kind, label, timestamp, properties FROM mg_nodes"
        ):
            try:
                nodes[row[0]] = GraphNode(
                    node_id=row[0],
                    kind=NodeKind(row[1]),
                    label=row[2] or "",
                    timestamp=row[3],
                    properties=json.loads(row[4]) if row[4] else {},
                )
            except (ValueError, json.JSONDecodeError):
                continue

        for row in self._conn.execute(
            "SELECT source_id, target_id, kind, label, properties FROM mg_edges"
        ):
            try:
                edges.append(GraphEdge(
                    source_id=row[0],
                    target_id=row[1],
                    kind=EdgeKind(row[2]),
                    label=row[3] or "",
                    properties=json.loads(row[4]) if row[4] else {},
                ))
            except (ValueError, json.JSONDecodeError):
                continue

        return nodes, edges

    def save_node(self, node: GraphNode) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO mg_nodes (node_id, kind, label, timestamp, properties) "
                "VALUES (?, ?, ?, ?, ?)",
                (node.node_id, node.kind.value, node.label, node.timestamp,
                 json.dumps(node.properties, default=str)),
            )
            self._conn.commit()

    def save_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO mg_edges (source_id, target_id, kind, label, properties) "
                "VALUES (?, ?, ?, ?, ?)",
                (edge.source_id, edge.target_id, edge.kind.value, edge.label,
                 json.dumps(edge.properties, default=str)),
            )
            self._conn.commit()

    def save_all(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM mg_nodes")
            self._conn.execute("DELETE FROM mg_edges")
            for node in nodes.values():
                self._conn.execute(
                    "INSERT INTO mg_nodes (node_id, kind, label, timestamp, properties) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (node.node_id, node.kind.value, node.label, node.timestamp,
                     json.dumps(node.properties, default=str)),
                )
            for edge in edges:
                self._conn.execute(
                    "INSERT INTO mg_edges (source_id, target_id, kind, label, properties) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (edge.source_id, edge.target_id, edge.kind.value, edge.label,
                     json.dumps(edge.properties, default=str)),
                )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class PostgreSQLMGBackend(MGPersistenceBackend):
    """PostgreSQL-based Memory Graph persistence using psycopg.

    Requires: pip install 'deepsigma[postgresql]'
    """

    _PG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS mg_nodes (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    label TEXT DEFAULT '',
    timestamp TEXT,
    properties JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS mg_edges (
    id SERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT DEFAULT '',
    properties JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
"""

    def __init__(self, conninfo: str) -> None:
        try:
            import psycopg
            import psycopg.pool
        except ImportError:
            raise ImportError(
                "psycopg is required for PostgreSQL backend: "
                "pip install 'deepsigma[postgresql]'"
            )
        self._psycopg = psycopg
        self._pool = psycopg.pool.ConnectionPool(conninfo, min_size=1, max_size=4)
        with self._pool.connection() as conn:
            conn.execute(self._PG_SCHEMA)
            conn.commit()

    def load(self) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        with self._pool.connection() as conn:
            for row in conn.execute(
                "SELECT node_id, kind, label, timestamp, properties FROM mg_nodes"
            ):
                try:
                    props = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
                    nodes[row[0]] = GraphNode(
                        node_id=row[0],
                        kind=NodeKind(row[1]),
                        label=row[2] or "",
                        timestamp=row[3],
                        properties=props,
                    )
                except (ValueError, json.JSONDecodeError):
                    continue

            for row in conn.execute(
                "SELECT source_id, target_id, kind, label, properties FROM mg_edges"
            ):
                try:
                    props = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
                    edges.append(GraphEdge(
                        source_id=row[0],
                        target_id=row[1],
                        kind=EdgeKind(row[2]),
                        label=row[3] or "",
                        properties=props,
                    ))
                except (ValueError, json.JSONDecodeError):
                    continue

        return nodes, edges

    def save_node(self, node: GraphNode) -> None:
        props = json.dumps(node.properties, default=str)
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO mg_nodes (node_id, kind, label, timestamp, properties) "
                "VALUES (%s, %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (node_id) DO UPDATE SET "
                "kind=EXCLUDED.kind, label=EXCLUDED.label, "
                "timestamp=EXCLUDED.timestamp, properties=EXCLUDED.properties",
                (node.node_id, node.kind.value, node.label, node.timestamp, props),
            )
            conn.commit()

    def save_edge(self, edge: GraphEdge) -> None:
        props = json.dumps(edge.properties, default=str)
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO mg_edges (source_id, target_id, kind, label, properties) "
                "VALUES (%s, %s, %s, %s, %s::jsonb)",
                (edge.source_id, edge.target_id, edge.kind.value, edge.label, props),
            )
            conn.commit()

    def save_all(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM mg_edges")
            conn.execute("DELETE FROM mg_nodes")
            for node in nodes.values():
                props = json.dumps(node.properties, default=str)
                conn.execute(
                    "INSERT INTO mg_nodes (node_id, kind, label, timestamp, properties) "
                    "VALUES (%s, %s, %s, %s, %s::jsonb)",
                    (node.node_id, node.kind.value, node.label, node.timestamp, props),
                )
            for edge in edges:
                props = json.dumps(edge.properties, default=str)
                conn.execute(
                    "INSERT INTO mg_edges (source_id, target_id, kind, label, properties) "
                    "VALUES (%s, %s, %s, %s, %s::jsonb)",
                    (edge.source_id, edge.target_id, edge.kind.value, edge.label, props),
                )
            conn.commit()

    def close(self) -> None:
        self._pool.close()
