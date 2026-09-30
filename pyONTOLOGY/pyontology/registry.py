from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .model import ModuleManifest, TermRecord, BridgeSuggestion
from .util import normalize_text


class SemanticRegistry:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS modules (
                module_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                namespace TEXT,
                owner TEXT,
                authority INTEGER NOT NULL,
                role TEXT NOT NULL,
                extension_of TEXT,
                dependencies_json TEXT NOT NULL,
                description TEXT,
                fingerprint TEXT NOT NULL,
                source_path TEXT
            );
            CREATE TABLE IF NOT EXISTS terms (
                uri TEXT NOT NULL,
                module_id TEXT NOT NULL,
                kinds_json TEXT NOT NULL,
                label TEXT NOT NULL,
                normalized_label TEXT NOT NULL,
                alt_labels_json TEXT NOT NULL,
                definition TEXT,
                comment TEXT,
                namespace TEXT,
                local_name TEXT,
                fingerprint TEXT,
                PRIMARY KEY (uri, module_id),
                FOREIGN KEY (module_id) REFERENCES modules(module_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_terms_norm_label ON terms(normalized_label);
            CREATE INDEX IF NOT EXISTS idx_terms_module ON terms(module_id);
            CREATE TABLE IF NOT EXISTS bridges (
                source_uri TEXT NOT NULL,
                target_uri TEXT NOT NULL,
                source_module TEXT NOT NULL,
                target_module TEXT NOT NULL,
                relation TEXT NOT NULL,
                score REAL NOT NULL,
                rationale TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (source_uri, target_uri, relation)
            );
            """
        )
        self.conn.commit()

    def register(self, module) -> None:
        m = module.manifest
        with self.conn:
            self.conn.execute("DELETE FROM modules WHERE module_id = ?", (m.module_id,))
            self.conn.execute(
                """INSERT INTO modules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    m.module_id, m.name, m.version, m.namespace, m.owner, m.authority, m.role,
                    m.extension_of, json.dumps(m.dependencies), m.description, module.fingerprint,
                    module.source_path,
                ),
            )
            self.conn.executemany(
                """INSERT INTO terms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        t.uri, t.module_id, json.dumps(t.kinds), t.label, normalize_text(t.label),
                        json.dumps(t.alt_labels), t.definition, t.comment, t.namespace,
                        t.local_name, t.fingerprint,
                    )
                    for t in module.terms()
                ],
            )

    def modules(self) -> list[ModuleManifest]:
        rows = self.conn.execute("SELECT * FROM modules ORDER BY module_id").fetchall()
        return [
            ModuleManifest(
                module_id=r["module_id"], name=r["name"], version=r["version"],
                namespace=r["namespace"], owner=r["owner"], authority=r["authority"],
                role=r["role"], extension_of=r["extension_of"],
                dependencies=json.loads(r["dependencies_json"]), description=r["description"],
            ) for r in rows
        ]

    def terms(self, module_id: str | None = None) -> list[TermRecord]:
        if module_id:
            rows = self.conn.execute("SELECT * FROM terms WHERE module_id=? ORDER BY label", (module_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM terms ORDER BY module_id, label").fetchall()
        return [self._row_to_term(r) for r in rows]

    def exact_label(self, label: str) -> list[TermRecord]:
        rows = self.conn.execute(
            "SELECT * FROM terms WHERE normalized_label=? ORDER BY module_id, label",
            (normalize_text(label),),
        ).fetchall()
        return [self._row_to_term(r) for r in rows]

    def save_bridge(self, bridge: BridgeSuggestion) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO bridges VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bridge.source_uri, bridge.target_uri, bridge.source_module, bridge.target_module,
                    bridge.relation, bridge.score, bridge.rationale, bridge.status,
                ),
            )

    def bridge_status(self, source_uri: str, target_uri: str) -> str | None:
        row = self.conn.execute(
            """SELECT status FROM bridges
               WHERE (source_uri=? AND target_uri=?) OR (source_uri=? AND target_uri=?)
               ORDER BY CASE status WHEN 'ACCEPTED' THEN 0 ELSE 1 END LIMIT 1""",
            (source_uri, target_uri, target_uri, source_uri),
        ).fetchone()
        return row["status"] if row else None

    def bridges(self) -> list[BridgeSuggestion]:
        rows = self.conn.execute("SELECT * FROM bridges ORDER BY score DESC").fetchall()
        return [BridgeSuggestion(**dict(r)) for r in rows]

    @staticmethod
    def _row_to_term(r: sqlite3.Row) -> TermRecord:
        return TermRecord(
            uri=r["uri"], module_id=r["module_id"], kinds=tuple(json.loads(r["kinds_json"])),
            label=r["label"], alt_labels=tuple(json.loads(r["alt_labels_json"])),
            definition=r["definition"], comment=r["comment"], namespace=r["namespace"],
            local_name=r["local_name"], fingerprint=r["fingerprint"],
        )

    def close(self) -> None:
        self.conn.close()
