"""Tests for StorageBackend implementations (SQLite + JSONL)."""

import pytest

from core.storage import (
    JSONLStorageBackend,
    SQLiteStorageBackend,
    create_backend,
)


SAMPLE_EVENT = {
    "event_id": "evt-001",
    "event_type": "episode_start",
    "timestamp": "2026-02-19T00:00:00Z",
    "payload": {"agentId": "agent-1"},
}

SAMPLE_EPISODE = {
    "episodeId": "ep-001",
    "decisionType": "deploy",
    "sealedAt": "2026-02-19T01:00:00Z",
    "outcome": {"code": "success"},
    "actions": [],
}

SAMPLE_DRIFT = {
    "driftId": "drift-001",
    "episodeId": "ep-001",
    "driftType": "freshness",
    "severity": "yellow",
    "detectedAt": "2026-02-19T02:00:00Z",
}

SAMPLE_DLR = {
    "dlrId": "DLR-abc123",
    "episodeId": "ep-001",
    "decisionType": "deploy",
    "recordedAt": "2026-02-19T01:00:00Z",
    "outcomeCode": "success",
    "tags": ["ci"],
}


# -- SQLite tests --


class TestSQLiteStorageEvents:
    def test_append_and_list(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.append_event(SAMPLE_EVENT)
        events = b.list_events()
        assert len(events) == 1
        assert events[0]["event_id"] == "evt-001"

    def test_duplicate_event_ignored(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.append_event(SAMPLE_EVENT)
        b.append_event(SAMPLE_EVENT)  # same event_id
        assert len(b.list_events()) == 1

    def test_list_pagination(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        for i in range(5):
            b.append_event({"event_id": f"evt-{i}", "event_type": "test"})
        assert len(b.list_events(limit=2)) == 2
        assert len(b.list_events(limit=10, offset=3)) == 2


class TestSQLiteStorageEpisodes:
    def test_save_and_get(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_episode(SAMPLE_EPISODE)
        ep = b.get_episode("ep-001")
        assert ep is not None
        assert ep["episodeId"] == "ep-001"
        assert ep["outcome"]["code"] == "success"

    def test_get_missing(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        assert b.get_episode("nonexistent") is None

    def test_upsert(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_episode(SAMPLE_EPISODE)
        updated = {**SAMPLE_EPISODE, "outcome": {"code": "failure"}}
        b.save_episode(updated)
        ep = b.get_episode("ep-001")
        assert ep["outcome"]["code"] == "failure"

    def test_list(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_episode(SAMPLE_EPISODE)
        b.save_episode({**SAMPLE_EPISODE, "episodeId": "ep-002", "sealedAt": "2026-02-19T02:00:00Z"})
        episodes = b.list_episodes()
        assert len(episodes) == 2


class TestSQLiteStorageDrift:
    def test_append_and_list(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.append_drift(SAMPLE_DRIFT)
        drifts = b.list_drifts()
        assert len(drifts) == 1
        assert drifts[0]["driftId"] == "drift-001"

    def test_duplicate_drift_ignored(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.append_drift(SAMPLE_DRIFT)
        b.append_drift(SAMPLE_DRIFT)
        assert len(b.list_drifts()) == 1


class TestSQLiteStorageDLR:
    def test_save_and_get(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_dlr(SAMPLE_DLR)
        dlr = b.get_dlr("DLR-abc123")
        assert dlr is not None
        assert dlr["episodeId"] == "ep-001"

    def test_get_missing(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        assert b.get_dlr("nonexistent") is None

    def test_upsert(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_dlr(SAMPLE_DLR)
        updated = {**SAMPLE_DLR, "outcomeCode": "failure"}
        b.save_dlr(updated)
        dlr = b.get_dlr("DLR-abc123")
        assert dlr["outcomeCode"] == "failure"

    def test_list(self, tmp_path):
        b = SQLiteStorageBackend(tmp_path / "test.db")
        b.save_dlr(SAMPLE_DLR)
        b.save_dlr({**SAMPLE_DLR, "dlrId": "DLR-def456", "recordedAt": "2026-02-19T02:00:00Z"})
        assert len(b.list_dlrs()) == 2


# -- JSONL tests --


class TestJSONLStorageEvents:
    def test_append_and_list(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        b.append_event(SAMPLE_EVENT)
        events = b.list_events()
        assert len(events) == 1
        assert events[0]["event_id"] == "evt-001"

    def test_multiple_events(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        for i in range(3):
            b.append_event({"event_id": f"evt-{i}", "event_type": "test"})
        assert len(b.list_events()) == 3


class TestJSONLStorageEpisodes:
    def test_save_and_get(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        b.save_episode(SAMPLE_EPISODE)
        ep = b.get_episode("ep-001")
        assert ep is not None
        assert ep["episodeId"] == "ep-001"

    def test_get_missing(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        assert b.get_episode("nonexistent") is None


class TestJSONLStorageDrift:
    def test_append_and_list(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        b.append_drift(SAMPLE_DRIFT)
        drifts = b.list_drifts()
        assert len(drifts) == 1


class TestJSONLStorageDLR:
    def test_save_and_get(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        b.save_dlr(SAMPLE_DLR)
        dlr = b.get_dlr("DLR-abc123")
        assert dlr is not None
        assert dlr["episodeId"] == "ep-001"

    def test_get_missing(self, tmp_path):
        b = JSONLStorageBackend(tmp_path)
        assert b.get_dlr("nonexistent") is None


# -- Factory tests --


class TestCreateBackend:
    def test_sqlite_url(self, tmp_path):
        url = f"sqlite:///{tmp_path}/factory.db"
        b = create_backend(url)
        assert isinstance(b, SQLiteStorageBackend)

    def test_jsonl_url(self, tmp_path):
        url = f"jsonl://{tmp_path}"
        b = create_backend(url)
        assert isinstance(b, JSONLStorageBackend)

    def test_empty_url_defaults_to_jsonl(self):
        b = create_backend("")
        assert isinstance(b, JSONLStorageBackend)

    def test_none_without_env_defaults_to_jsonl(self, monkeypatch):
        monkeypatch.delenv("DEEPSIGMA_STORAGE_URL", raising=False)
        b = create_backend(None)
        assert isinstance(b, JSONLStorageBackend)

    def test_env_var_fallback(self, tmp_path, monkeypatch):
        url = f"sqlite:///{tmp_path}/env.db"
        monkeypatch.setenv("DEEPSIGMA_STORAGE_URL", url)
        b = create_backend(None)
        assert isinstance(b, SQLiteStorageBackend)

    def test_unsupported_scheme_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            create_backend("mysql://localhost/db")

    def test_postgresql_without_psycopg_raises(self):
        with pytest.raises((ImportError, ValueError)):
            create_backend("postgresql://localhost/db")


class TestSchemaCreation:
    def test_sqlite_creates_tables(self, tmp_path):
        import sqlite3
        SQLiteStorageBackend(tmp_path / "schema.db")
        conn = sqlite3.connect(str(tmp_path / "schema.db"))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        for expected in ["events", "episodes", "drifts", "dlrs", "schema_version"]:
            assert expected in tables
        conn.close()
