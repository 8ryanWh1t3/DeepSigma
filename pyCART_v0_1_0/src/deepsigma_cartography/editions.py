"""Append-only SQLite map editions. Integrity hashes are not authentication."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .atlas import Atlas
from .util import ConflictError, IntegrityError, Record, ValidationError, canonical_json, digest, instant, parse_json, text, timestamp


@dataclass(frozen=True)
class Edition(Record):
    sequence: int
    recorded_at: str
    parent_hash: str | None
    atlas: Atlas
    content_hash: str
    edition_hash: str
    record_kind: str = "cartographic_snapshot_not_authorization"

    def body(self) -> dict[str, Any]:
        return {k: v for k, v in self.to_dict().items() if k != "edition_hash"}


@dataclass(frozen=True)
class Delta(Record):
    collection: str
    id: str
    change: str
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class MapDiff(Record):
    before_fingerprint: str
    after_fingerprint: str
    deltas: tuple[Delta, ...]


def compare(before: Atlas, after: Atlas) -> MapDiff:
    if before.id != after.id:
        raise ValidationError("Edition comparison requires the same atlas identity")
    result = []
    for name in ("nodes", "edges", "evidence", "predicates"):
        left = {r.id: r.to_dict() for r in getattr(before, name)}
        right = {r.id: r.to_dict() for r in getattr(after, name)}
        for key in sorted(left.keys() | right.keys()):
            if key not in left:
                result.append(Delta(name, key, "added"))
            elif key not in right:
                result.append(Delta(name, key, "removed"))
            elif canonical_json(left[key]) != canonical_json(right[key]):
                fields = tuple(k for k in sorted(left[key].keys() | right[key].keys())
                               if canonical_json(left[key].get(k)) != canonical_json(right[key].get(k)))
                result.append(Delta(name, key, "modified", fields))
    fields = tuple(k for k in ("title", "attributes")
                   if canonical_json(getattr(before, k)) != canonical_json(getattr(after, k)))
    if fields:
        result.append(Delta("atlas", before.id, "modified", fields))
    return MapDiff(before.fingerprint, after.fingerprint, tuple(result))


class EditionStore:
    """A trusted-host local archive, not an authority service or hostile-host defense.

    create() explicitly bootstraps a NEW file. open() never creates missing storage.
    Each append verifies the chain, uses BEGIN IMMEDIATE and checks expected_parent.
    An independently retained expected_head detects restoration of an older DB copy.
    """
    def __init__(self, connection: sqlite3.Connection, path: Path):
        self._db = connection
        self.path = path

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        uri = "file:" + quote(str(path.absolute()), safe="/") + "?mode=rw"
        connection = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5)
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @classmethod
    def create(cls, path: str | Path, *, atlas_id: str) -> EditionStore:
        text(atlas_id, "atlas_id")
        path = Path(path)
        # Exclusive creation is intentional. Never turn a missing/corrupt archive into genesis on open.
        with path.open("xb"):
            pass
        connection = None
        try:
            connection = cls._connect(path)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), schema_version INTEGER NOT NULL, atlas_id TEXT NOT NULL, head_seq INTEGER NOT NULL, head_hash TEXT)")
            connection.execute("CREATE TABLE editions (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, hash TEXT NOT NULL UNIQUE)")
            connection.execute("INSERT INTO meta VALUES(1,1,?,0,NULL)", (atlas_id,))
            connection.commit()
            return cls(connection, path)
        except Exception:
            if connection:
                connection.close()
            path.unlink(missing_ok=True)
            raise

    @classmethod
    def open(cls, path: str | Path, *, expected_head: str | None = None) -> EditionStore:
        path = Path(path)
        connection = None
        try:
            connection = cls._connect(path)
            store = cls(connection, path)
            store.verify(expected_head=expected_head)
            return store
        except (sqlite3.Error, IntegrityError, ValidationError) as exc:
            if connection:
                connection.close()
            raise IntegrityError(f"Archive cannot be opened and verified: {exc}") from exc

    def _verified(self) -> list[Edition]:
        try:
            metadata = self._db.execute("SELECT schema_version,atlas_id,head_seq,head_hash FROM meta WHERE id=1").fetchone()
            if metadata is None or metadata[0] != 1:
                raise IntegrityError("Missing or unsupported archive metadata")
            _, atlas_id, head_seq, head_hash = metadata
            if type(head_seq) is not int or head_seq < 0:
                raise IntegrityError("Invalid head sequence")
            rows = self._db.execute("SELECT seq,body,hash FROM editions ORDER BY seq").fetchall()
            result: list[Edition] = []
            parent = None
            previous_time = None
            for expected_seq, (seq, body_text, recorded_hash) in enumerate(rows, 1):
                body = parse_json(body_text)
                if seq != expected_seq or body.get("sequence") != seq or body.get("parent_hash") != parent:
                    raise IntegrityError("Edition sequence or parent link is broken")
                if digest(body) != recorded_hash:
                    raise IntegrityError("Edition digest mismatch")
                atlas = Atlas.from_dict(body["atlas"])
                if atlas.id != atlas_id or atlas.fingerprint != body["content_hash"]:
                    raise IntegrityError("Atlas identity or content digest mismatch")
                at = timestamp(body["recorded_at"])
                if previous_time and instant(at) < instant(previous_time):
                    raise IntegrityError("Edition timestamps moved backward")
                edition = Edition(seq, at, parent, atlas, body["content_hash"], recorded_hash)
                if canonical_json(edition.body()) != canonical_json(body):
                    raise IntegrityError("Unexpected or noncanonical edition fields")
                result.append(edition)
                parent, previous_time = recorded_hash, at
            if len(rows) != head_seq or parent != head_hash:
                raise IntegrityError("Archive head disagrees with stored editions")
            return result
        except (sqlite3.Error, KeyError, TypeError, AttributeError, ValidationError) as exc:
            raise IntegrityError(f"Invalid archive: {exc}") from exc

    def verify(self, *, expected_head: str | None = None) -> str | None:
        # A read transaction prevents concurrent append from mixing two DB snapshots.
        own_transaction = not self._db.in_transaction
        try:
            if own_transaction:
                self._db.execute("BEGIN")
            rows = self._verified()
            head = rows[-1].edition_hash if rows else None
            if expected_head is not None and head != expected_head:
                raise IntegrityError("Archive does not match the independently pinned head")
            if own_transaction:
                self._db.commit()
            return head
        except Exception:
            if own_transaction:
                self._db.rollback()
            raise

    @property
    def head(self) -> str | None:
        return self.verify()

    def append(self, atlas: Atlas, *, recorded_at: str, expected_parent: str | None) -> Edition:
        if not isinstance(atlas, Atlas):
            raise ValidationError("append requires an Atlas")
        recorded_at = timestamp(recorded_at)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            rows = self._verified()
            parent = rows[-1].edition_hash if rows else None
            if parent != expected_parent:
                raise ConflictError("Archive advanced: expected_parent does not match the current head")
            atlas_id = self._db.execute("SELECT atlas_id FROM meta WHERE id=1").fetchone()[0]
            if atlas.id != atlas_id:
                raise ValidationError("Atlas identity differs from this archive")
            if rows and instant(recorded_at) < instant(rows[-1].recorded_at):
                raise ValidationError("recorded_at cannot move backward")
            entry = Edition(len(rows) + 1, recorded_at, parent, atlas, atlas.fingerprint, "")
            body = entry.body()
            new_hash = digest(body)
            self._db.execute("INSERT INTO editions VALUES(?,?,?)", (entry.sequence, canonical_json(body), new_hash))
            self._db.execute("UPDATE meta SET head_seq=?,head_hash=? WHERE id=1", (entry.sequence, new_hash))
            # Verify written rows before the transaction commits; all failures propagate.
            inserted = self._verified()[-1]
            self._db.commit()
            return inserted
        except Exception:
            self._db.rollback()
            raise

    def editions(self) -> tuple[Edition, ...]:
        try:
            self._db.execute("BEGIN")
            result = tuple(self._verified())
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    def get(self, sequence: int) -> Edition:
        if type(sequence) is not int or sequence < 1:
            raise ValidationError("sequence must be a positive integer")
        rows = self.editions()
        if sequence > len(rows):
            raise ValidationError("Edition not found")
        return rows[sequence - 1]

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> EditionStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
