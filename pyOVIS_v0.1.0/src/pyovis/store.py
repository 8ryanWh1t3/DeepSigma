from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .schemas import SearchHit, SemanticObject

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS semantic_object (
    id TEXT PRIMARY KEY,
    modality TEXT NOT NULL,
    uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    text_content TEXT,
    page INTEGER,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS embedding (
    object_id TEXT PRIMARY KEY REFERENCES semantic_object(id) ON DELETE CASCADE,
    backend TEXT NOT NULL,
    model TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_object_sha ON semantic_object(sha256);
CREATE INDEX IF NOT EXISTS idx_object_modality ON semantic_object(modality);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SemanticStore:
    def __init__(self, path: str | Path):
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def upsert(self, obj: SemanticObject, vector: np.ndarray, backend: str, model: str) -> None:
        vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        now = _now()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO semantic_object
                (id, modality, uri, sha256, size_bytes, mtime_ns, text_content, page, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  modality=excluded.modality, uri=excluded.uri, sha256=excluded.sha256,
                  size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns,
                  text_content=excluded.text_content, page=excluded.page,
                  metadata_json=excluded.metadata_json
                """,
                (obj.id, obj.modality, obj.uri, obj.sha256, obj.size_bytes, obj.mtime_ns,
                 obj.text, obj.page, json.dumps(obj.metadata, sort_keys=True), now),
            )
            conn.execute(
                """INSERT INTO embedding (object_id, backend, model, dimension, vector, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(object_id) DO UPDATE SET
                  backend=excluded.backend, model=excluded.model, dimension=excluded.dimension,
                  vector=excluded.vector, created_at=excluded.created_at
                """,
                (obj.id, backend, model, vector.size, vector.tobytes(), now),
            )

    def get_object(self, object_id: str) -> SemanticObject | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, modality, uri, sha256, size_bytes, mtime_ns, text_content, page, metadata_json "
                "FROM semantic_object WHERE id=?",
                (object_id,),
            ).fetchone()
        if row is None:
            return None
        return SemanticObject(
            id=row[0], modality=row[1], uri=row[2], sha256=row[3], size_bytes=row[4],
            mtime_ns=row[5], text=row[6], page=row[7], metadata=json.loads(row[8]),
        )

    def get_vector(self, object_id: str) -> np.ndarray | None:
        with self.connect() as conn:
            row = conn.execute("SELECT dimension, vector FROM embedding WHERE object_id=?", (object_id,)).fetchone()
        if row is None:
            return None
        dim, blob = row
        vec = np.frombuffer(blob, dtype=np.float32).copy()
        if vec.size != dim:
            raise ValueError(f"Corrupt vector for {object_id}: expected {dim}, got {vec.size}")
        return vec

    def iter_vectors(self):
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT o.id, o.modality, o.uri, o.text_content, o.metadata_json,
                          e.dimension, e.vector
                   FROM semantic_object o JOIN embedding e ON e.object_id=o.id"""
            ).fetchall()
        for row in rows:
            vec = np.frombuffer(row[6], dtype=np.float32).copy()
            if vec.size != row[5]:
                continue
            yield row[0], row[1], row[2], row[3], json.loads(row[4]), vec

    def search(self, query: np.ndarray, top_k: int = 10, exclude_id: str | None = None) -> list[SearchHit]:
        query = np.asarray(query, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(query))
        if norm == 0:
            raise ValueError("Query vector norm is zero")
        query = query / norm
        hits = []
        for oid, modality, uri, text, metadata, vec in self.iter_vectors():
            if exclude_id and oid == exclude_id:
                continue
            if vec.size != query.size:
                continue
            vnorm = float(np.linalg.norm(vec))
            if vnorm == 0:
                continue
            score = float(np.dot(query, vec / vnorm))
            hits.append(SearchHit(oid, score, modality, uri, text, metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: max(0, top_k)]

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM semantic_object").fetchone()[0])

    def stats(self) -> dict:
        with self.connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) FROM semantic_object").fetchone()[0])
            by_modality = dict(conn.execute(
                "SELECT modality, COUNT(*) FROM semantic_object GROUP BY modality ORDER BY modality"
            ).fetchall())
            models = [dict(zip(("backend", "model", "dimension", "count"), row)) for row in conn.execute(
                "SELECT backend, model, dimension, COUNT(*) FROM embedding GROUP BY backend, model, dimension"
            ).fetchall()]
        return {"total_objects": total, "by_modality": by_modality, "embeddings": models}
