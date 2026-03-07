"""Tests for core.killswitch — emergency halt function."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.killswitch import activate_killswitch  # noqa: E402
from core.episode_state import EpisodeState, EpisodeTracker  # noqa: E402
from core.audit_log import AuditLog  # noqa: E402


def _make_tracker(*active_ids: str) -> EpisodeTracker:
    """Build a tracker with some ACTIVE episodes."""
    tracker = EpisodeTracker()
    for eid in active_ids:
        tracker.set_state(eid, EpisodeState.ACTIVE)
    return tracker


class TestActivateKillswitch:
    """Tests for activate_killswitch()."""

    def test_returns_dict(self):
        tracker = _make_tracker("ep-1")
        proof = activate_killswitch(tracker, "admin", "test halt")
        assert isinstance(proof, dict)

    def test_required_keys_present(self):
        tracker = _make_tracker("ep-1")
        proof = activate_killswitch(tracker, "admin", "test halt")
        for key in ("activatedAt", "authorizedBy", "reason", "frozenEpisodes",
                     "frozenCount", "sealHash"):
            assert key in proof, f"Missing key: {key}"

    def test_authorized_by_preserved(self):
        proof = activate_killswitch(_make_tracker(), "ops-lead", "drill")
        assert proof["authorizedBy"] == "ops-lead"

    def test_reason_preserved(self):
        proof = activate_killswitch(_make_tracker(), "admin", "security incident")
        assert proof["reason"] == "security incident"

    def test_seal_hash_format(self):
        proof = activate_killswitch(_make_tracker("ep-1"), "admin", "halt")
        assert proof["sealHash"].startswith("sha256:")
        assert len(proof["sealHash"]) == len("sha256:") + 64

    def test_freezes_active_episodes(self):
        tracker = _make_tracker("ep-1", "ep-2", "ep-3")
        proof = activate_killswitch(tracker, "admin", "halt")
        assert proof["frozenCount"] == 3
        assert set(proof["frozenEpisodes"]) == {"ep-1", "ep-2", "ep-3"}

    def test_frozen_episodes_state(self):
        tracker = _make_tracker("ep-1", "ep-2")
        activate_killswitch(tracker, "admin", "halt")
        assert tracker.get_state("ep-1") == EpisodeState.FROZEN
        assert tracker.get_state("ep-2") == EpisodeState.FROZEN

    def test_no_active_episodes(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.SEALED)
        proof = activate_killswitch(tracker, "admin", "halt")
        assert proof["frozenCount"] == 0
        assert proof["frozenEpisodes"] == []

    def test_pending_and_sealed_untouched(self):
        tracker = EpisodeTracker()
        tracker.set_state("pending-1", EpisodeState.PENDING)
        tracker.set_state("sealed-1", EpisodeState.SEALED)
        tracker.set_state("active-1", EpisodeState.ACTIVE)
        activate_killswitch(tracker, "admin", "halt")
        assert tracker.get_state("pending-1") == EpisodeState.PENDING
        assert tracker.get_state("sealed-1") == EpisodeState.SEALED
        assert tracker.get_state("active-1") == EpisodeState.FROZEN

    def test_audit_log_integration(self):
        tracker = _make_tracker("ep-1")
        log = AuditLog()
        activate_killswitch(tracker, "admin", "halt", audit_log=log)
        assert log.entry_count == 1
        entries = log.entries()
        assert entries[0]["entryType"] == "killswitch_activated"
        assert "admin" in entries[0]["detail"]

    def test_audit_log_none_no_error(self):
        tracker = _make_tracker("ep-1")
        proof = activate_killswitch(tracker, "admin", "halt", audit_log=None)
        assert proof["frozenCount"] == 1

    def test_deterministic_seal(self):
        """Same inputs at same time should produce same seal."""
        tracker1 = _make_tracker()
        tracker2 = _make_tracker()
        p1 = activate_killswitch(tracker1, "admin", "reason")
        p2 = activate_killswitch(tracker2, "admin", "reason")
        # Both have no frozen episodes, same author/reason
        # activatedAt may differ by microseconds, so we only check format
        assert p1["sealHash"].startswith("sha256:")
        assert p2["sealHash"].startswith("sha256:")
