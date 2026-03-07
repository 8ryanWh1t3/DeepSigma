"""Tests for core.episode_state — lifecycle state machine."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.episode_state import EpisodeState, EpisodeTracker  # noqa: E402


class TestEpisodeState:
    """Tests for the EpisodeState enum."""

    def test_five_states(self):
        assert len(EpisodeState) == 5

    def test_enum_values(self):
        assert EpisodeState.PENDING.value == "pending"
        assert EpisodeState.ACTIVE.value == "active"
        assert EpisodeState.SEALED.value == "sealed"
        assert EpisodeState.ARCHIVED.value == "archived"
        assert EpisodeState.FROZEN.value == "frozen"

    def test_str_enum(self):
        assert isinstance(EpisodeState.PENDING, str)
        assert EpisodeState.PENDING == "pending"


class TestEpisodeTracker:
    """Tests for the EpisodeTracker class."""

    def test_set_and_get_state(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        assert tracker.get_state("ep-1") == EpisodeState.ACTIVE

    def test_get_unknown_returns_none(self):
        tracker = EpisodeTracker()
        assert tracker.get_state("nonexistent") is None

    def test_valid_transition_pending_to_active(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.PENDING)
        assert tracker.transition("ep-1", EpisodeState.ACTIVE) is True
        assert tracker.get_state("ep-1") == EpisodeState.ACTIVE

    def test_valid_transition_active_to_sealed(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        assert tracker.transition("ep-1", EpisodeState.SEALED) is True

    def test_valid_transition_active_to_frozen(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        assert tracker.transition("ep-1", EpisodeState.FROZEN) is True

    def test_valid_transition_sealed_to_archived(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.SEALED)
        assert tracker.transition("ep-1", EpisodeState.ARCHIVED) is True

    def test_valid_transition_frozen_to_active(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.FROZEN)
        assert tracker.transition("ep-1", EpisodeState.ACTIVE) is True

    def test_invalid_transition_pending_to_sealed(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.PENDING)
        assert tracker.transition("ep-1", EpisodeState.SEALED) is False
        assert tracker.get_state("ep-1") == EpisodeState.PENDING

    def test_invalid_transition_archived_to_any(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ARCHIVED)
        for target in EpisodeState:
            assert tracker.transition("ep-1", target) is False

    def test_transition_new_episode(self):
        tracker = EpisodeTracker()
        assert tracker.transition("ep-new", EpisodeState.PENDING) is True
        assert tracker.get_state("ep-new") == EpisodeState.PENDING

    def test_freeze_all_active(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        tracker.set_state("ep-2", EpisodeState.ACTIVE)
        tracker.set_state("ep-3", EpisodeState.SEALED)
        frozen = tracker.freeze_all()
        assert set(frozen) == {"ep-1", "ep-2"}
        assert tracker.get_state("ep-1") == EpisodeState.FROZEN
        assert tracker.get_state("ep-3") == EpisodeState.SEALED

    def test_freeze_all_none_active(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.SEALED)
        assert tracker.freeze_all() == []

    def test_active_episodes(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        tracker.set_state("ep-2", EpisodeState.SEALED)
        tracker.set_state("ep-3", EpisodeState.ACTIVE)
        active = tracker.active_episodes()
        assert set(active) == {"ep-1", "ep-3"}

    def test_all_states(self):
        tracker = EpisodeTracker()
        tracker.set_state("ep-1", EpisodeState.ACTIVE)
        tracker.set_state("ep-2", EpisodeState.SEALED)
        result = tracker.all_states()
        assert result == {"ep-1": "active", "ep-2": "sealed"}
        assert isinstance(result, dict)
