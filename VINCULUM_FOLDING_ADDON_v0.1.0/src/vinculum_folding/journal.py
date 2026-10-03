"""Explicit local SQLite snapshot journal; not the CERPA authority service.

Normal API writes are append-only. Internal hash consistency is NOT a guarantee
against someone rewriting the database and recomputing the entire chain. Retain
an independently protected expected tip to detect rollback/substitution.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .model import FoldEpisode, FoldError, timestamp

FORMAT = "vinculum.folding.sqlite/1"


class EpisodeJournal:
    def __init__(self, connection: sqlite3.Connection, *, read_only: bool):
        self._db, self.read_only = connection, read_only
        try:
            rows = self._db.execute("SELECT value FROM metadata WHERE key='format'").fetchall()
            if rows != [(FORMAT,)]:
                raise FoldError("not a supported folding journal")
            self._db.execute("SELECT episode_id, revision, digest, payload FROM episodes LIMIT 0")
        except (sqlite3.Error, FoldError) as exc:
            self._db.close()
            raise FoldError("journal format is invalid or corrupt") from exc

    @classmethod
    def create(cls, path: str | Path) -> "EpisodeJournal":
        """Explicit first creation; refuse existing paths instead of resetting history."""
        path = Path(path).resolve()
        with path.open("xb"):
            pass
        con = sqlite3.connect(path)
        try:
            con.execute("PRAGMA synchronous=FULL")
            con.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE episodes(
                    episode_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    digest TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(episode_id, revision));
            """)
            con.execute("INSERT INTO metadata VALUES('format', ?)", (FORMAT,))
            con.commit()
            return cls(con, read_only=False)
        except BaseException:
            con.close()
            # Leave the failed initial file for explicit operator inspection/recovery.
            raise

    @classmethod
    def open(cls, path: str | Path, *, read_only: bool = True) -> "EpisodeJournal":
        if type(read_only) is not bool:
            raise FoldError("read_only must be boolean")
        path = Path(path).resolve()
        mode = "ro" if read_only else "rw"  # neither mode recreates missing history
        try:
            con = sqlite3.connect(path.as_uri() + f"?mode={mode}", uri=True, timeout=5)
            if not read_only:
                con.execute("PRAGMA synchronous=FULL")
            return cls(con, read_only=read_only)
        except sqlite3.Error as exc:
            raise FoldError("journal unavailable; no replacement history was created") from exc

    def _history(self, episode_id: str) -> tuple[FoldEpisode, ...]:
        from .model import strict_json
        try:
            rows = self._db.execute("SELECT revision, digest, payload FROM episodes WHERE episode_id=? ORDER BY revision", (episode_id,)).fetchall()
            episodes, previous, mission, last_time = [], None, None, None
            for expected, (revision, stored_digest, payload) in enumerate(rows, 1):
                ep = FoldEpisode(strict_json(payload))
                data = ep.to_dict()
                if revision != expected or ep.revision != revision or ep.episode_id != episode_id or ep.digest != stored_digest or data["previous_digest"] != previous:
                    raise FoldError("journal continuity/identity/hash check failed")
                if mission is not None and data["mission_id"] != mission:
                    raise FoldError("mission changed within one episode history")
                now = timestamp(data["recorded_at"])
                if last_time is not None and now < last_time:
                    raise FoldError("recorded-at chronology moved backward")
                mission, previous, last_time = data["mission_id"], ep.digest, now
                episodes.append(ep)
            return tuple(episodes)
        except (sqlite3.Error, UnicodeError) as exc:
            raise FoldError("journal read failed or stored history is corrupt") from exc

    def history(self, episode_id: str) -> tuple[FoldEpisode, ...]:
        return self._history(episode_id)

    def get(self, episode_id: str, revision: int | None = None) -> FoldEpisode:
        history = self._history(episode_id)
        if not history:
            raise FoldError("episode is not present in journal")
        if revision is None:
            return history[-1]
        if type(revision) is not int or not 1 <= revision <= len(history):
            raise FoldError("requested revision is not present")
        return history[revision - 1]

    def verify(self, episode_id: str, *, expected_tip: str | None = None) -> dict:
        history = self._history(episode_id)
        if not history:
            raise FoldError("cannot verify absent episode history")
        if expected_tip is not None and history[-1].digest != expected_tip:
            raise FoldError("journal tip differs from independently expected content")
        return {"episode_id": episode_id, "revisions": len(history),
                "tip_digest": history[-1].digest, "internally_consistent": True,
                "expected_tip_checked": expected_tip is not None,
                "boundary": "Local content continuity only; not trusted authority, source authenticity or proof of successful APPLY."}

    def append(self, episode: FoldEpisode) -> str:
        if self.read_only:
            raise FoldError("read-only journal cannot append")
        if not isinstance(episode, FoldEpisode):
            raise FoldError("append requires a validated episode")
        data = episode.to_dict()
        try:
            self._db.execute("BEGIN IMMEDIATE")
            history = self._history(episode.episode_id)
            expected_revision = len(history) + 1
            expected_hash = history[-1].digest if history else None
            if episode.revision != expected_revision or data["previous_digest"] != expected_hash:
                raise FoldError("stale revision or wrong predecessor; append refused")
            if history:
                prior = history[-1].to_dict()
                if data["mission_id"] != prior["mission_id"]:
                    raise FoldError("mission identity cannot change across revisions")
                if timestamp(data["recorded_at"]) < timestamp(prior["recorded_at"]):
                    raise FoldError("recorded_at must not move backward; event time is a separate aspect")
            self._db.execute("INSERT INTO episodes VALUES(?,?,?,?)",
                             (episode.episode_id, episode.revision, episode.digest, episode._json))
            row = self._db.execute("SELECT digest, payload FROM episodes WHERE episode_id=? AND revision=?",
                                   (episode.episode_id, episode.revision)).fetchone()
            if row != (episode.digest, episode._json):
                raise FoldError("journal read-back differs from appended snapshot")
            self._db.commit()
            return episode.digest
        except (sqlite3.Error, FoldError) as exc:
            self._db.rollback()
            if isinstance(exc, FoldError):
                raise
            raise FoldError("journal append failed; transaction rolled back") from exc

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
