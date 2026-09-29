from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import MissionObject, MissionObjectKind


class SQLiteStore:
    """Durable append-only storage for a peer's mission objects."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mission_objects (
                object_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def put(self, obj: MissionObject) -> None:
        payload = {
            "object_id": obj.object_id,
            "kind": obj.kind.value,
            "entity_id": obj.entity_id,
            "field": obj.field,
            "value": obj.value,
            "origin_peer": obj.origin_peer,
            "observed_at": obj.observed_at.isoformat(),
            "created_at": obj.created_at.isoformat(),
            "confidence": obj.confidence,
            "authority_id": obj.authority_id,
            "evidence": list(obj.evidence),
            "dependencies": list(obj.dependencies),
            "classification": obj.classification,
            "releasability": list(obj.releasability),
            "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
            "version": obj.version,
            "supersedes": obj.supersedes,
            "metadata": dict(obj.metadata),
        }
        self._conn.execute(
            "INSERT OR IGNORE INTO mission_objects(object_id,payload,created_at) VALUES(?,?,?)",
            (obj.object_id, json.dumps(payload, sort_keys=True), obj.created_at.isoformat()),
        )
        self._conn.commit()

    def load_all(self) -> tuple[MissionObject, ...]:
        rows = self._conn.execute("SELECT payload FROM mission_objects ORDER BY created_at, object_id").fetchall()
        objects: list[MissionObject] = []
        for (payload_text,) in rows:
            p = json.loads(payload_text)
            objects.append(
                MissionObject(
                    object_id=p["object_id"],
                    kind=MissionObjectKind(p["kind"]),
                    entity_id=p["entity_id"],
                    field=p["field"],
                    value=p["value"],
                    origin_peer=p["origin_peer"],
                    observed_at=datetime.fromisoformat(p["observed_at"]),
                    created_at=datetime.fromisoformat(p["created_at"]),
                    confidence=p["confidence"],
                    authority_id=p["authority_id"],
                    evidence=tuple(p["evidence"]),
                    dependencies=tuple(p["dependencies"]),
                    classification=p["classification"],
                    releasability=tuple(p["releasability"]),
                    expires_at=datetime.fromisoformat(p["expires_at"]) if p["expires_at"] else None,
                    version=p["version"],
                    supersedes=p["supersedes"],
                    metadata=p["metadata"],
                )
            )
        return tuple(objects)

    def close(self) -> None:
        self._conn.close()
