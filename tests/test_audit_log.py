"""Tests for core.audit_log — hash-chained append-only audit log."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.audit_log import AuditEntry, AuditLog  # noqa: E402


def _make_entry(**overrides) -> AuditEntry:
    """Build a minimal AuditEntry."""
    defaults = {
        "entry_type": "test_event",
        "episode_id": "ep-001",
        "function_id": "fn-001",
        "detail": "test detail",
        "actor": "test-actor",
    }
    defaults.update(overrides)
    return AuditEntry(**defaults)


class TestAuditEntry:
    """Tests for the AuditEntry class."""

    def test_fields_set(self):
        entry = _make_entry()
        assert entry.entry_type == "test_event"
        assert entry.episode_id == "ep-001"
        assert entry.function_id == "fn-001"
        assert entry.detail == "test detail"
        assert entry.actor == "test-actor"

    def test_timestamp_iso(self):
        entry = _make_entry()
        assert "T" in entry.timestamp
        assert entry.timestamp.endswith("+00:00") or entry.timestamp.endswith("Z")

    def test_default_metadata_empty(self):
        entry = _make_entry()
        assert entry.metadata == {}

    def test_custom_metadata(self):
        entry = _make_entry(metadata={"key": "val"})
        assert entry.metadata == {"key": "val"}

    def test_chain_hash_initially_empty(self):
        entry = _make_entry()
        assert entry.chain_hash == ""

    def test_to_dict_keys(self):
        entry = _make_entry()
        d = entry.to_dict()
        expected = {"timestamp", "entryType", "episodeId", "functionId",
                     "detail", "actor", "metadata", "chainHash"}
        assert set(d.keys()) == expected

    def test_to_dict_camel_case(self):
        d = _make_entry().to_dict()
        assert "entryType" in d
        assert "entry_type" not in d


class TestAuditLog:
    """Tests for the AuditLog class."""

    def test_empty_log(self):
        log = AuditLog()
        assert log.entry_count == 0
        assert log.last_hash == "sha256:genesis"

    def test_append_returns_hash(self):
        log = AuditLog()
        h = log.append(_make_entry())
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_entry_count_increments(self):
        log = AuditLog()
        log.append(_make_entry())
        log.append(_make_entry(entry_type="second"))
        assert log.entry_count == 2

    def test_last_hash_updates(self):
        log = AuditLog()
        h1 = log.append(_make_entry())
        assert log.last_hash == h1
        h2 = log.append(_make_entry(entry_type="second"))
        assert log.last_hash == h2
        assert h1 != h2

    def test_entries_returns_list(self):
        log = AuditLog()
        log.append(_make_entry())
        entries = log.entries()
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert entries[0]["entryType"] == "test_event"

    def test_chain_hash_set_on_entry(self):
        log = AuditLog()
        entry = _make_entry()
        h = log.append(entry)
        assert entry.chain_hash == h

    def test_verify_chain_empty(self):
        log = AuditLog()
        assert log.verify_chain() is True

    def test_verify_chain_valid(self):
        log = AuditLog()
        log.append(_make_entry())
        log.append(_make_entry(entry_type="second"))
        log.append(_make_entry(entry_type="third"))
        assert log.verify_chain() is True

    def test_verify_chain_tamper_detected(self):
        log = AuditLog()
        log.append(_make_entry())
        log.append(_make_entry(entry_type="second"))
        # Tamper with the first entry's chain hash
        log._entries[0].chain_hash = "sha256:tampered"
        assert log.verify_chain() is False

    def test_chain_links_are_unique(self):
        log = AuditLog()
        hashes = set()
        for i in range(5):
            h = log.append(_make_entry(entry_type=f"event-{i}"))
            hashes.add(h)
        assert len(hashes) == 5
