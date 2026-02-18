"""Tests for standalone DriftDetector."""
import json

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    DriftType,
    EpisodeEvent,
    EventType,
    Source,
)
from engine.drift_detector import DriftDetector


def _make_episode(episode_id="ep-test", events=None):
    """Helper to build a minimal DecisionEpisode."""
    return DecisionEpisode(
        episode_id=episode_id,
        session_id="sess-1",
        events=events or [],
    )


def _make_event(event_type="metric", payload=None):
    return EpisodeEvent(
        event_id="evt-1",
        episode_id="ep-test",
        event_type=EventType(event_type),
        source=Source.manual,
        payload=payload or {},
    )


class TestDriftDetector:
    def test_no_drift_empty_episode(self, tmp_path):
        detector = DriftDetector(canon_path=tmp_path / "mg" / "memory_graph.jsonl")
        episode = _make_episode()
        signals = detector.detect_from_episode(episode.model_dump())
        assert signals == []

    def test_low_claim_coverage(self, tmp_path):
        """Episode with 3+ events but no extractable truth claims triggers low_claim_coverage."""
        events = [
            _make_event("prompt", {"text": "hello"}),
            _make_event("prompt", {"text": "world"}),
            _make_event("prompt", {"text": "test"}),
        ]
        detector = DriftDetector(canon_path=tmp_path / "mg" / "memory_graph.jsonl")
        episode = _make_episode(events=events)
        signals = detector.detect_from_episode(episode.model_dump())
        assert any(s.drift_type == DriftType.low_claim_coverage for s in signals)

    def test_contradiction(self, tmp_path):
        """Contradiction detected when canon has different value for same entity+property."""
        mg_dir = tmp_path / "mg"
        mg_dir.mkdir(parents=True)
        canon_file = mg_dir / "memory_graph.jsonl"
        canon_entry = {
            "node_type": "truth",
            "entity": "cpu_usage",
            "property_name": "cpu_usage",
            "value": "50",
        }
        canon_file.write_text(json.dumps(canon_entry) + "\n")

        events = [
            _make_event("metric", {"name": "cpu_usage", "value": 99}),
        ]
        detector = DriftDetector(canon_path=canon_file)
        episode = _make_episode(events=events)
        signals = detector.detect_from_episode(episode.model_dump())
        assert any(s.drift_type == DriftType.contradiction for s in signals)

    def test_no_canon_no_contradiction(self, tmp_path):
        """No contradiction when canon doesn't exist."""
        events = [
            _make_event("metric", {"name": "cpu_usage", "value": 99}),
        ]
        detector = DriftDetector(canon_path=tmp_path / "nonexistent.jsonl")
        episode = _make_episode(events=events)
        signals = detector.detect_from_episode(episode.model_dump())
        assert not any(s.drift_type == DriftType.contradiction for s in signals)

    def test_accepts_episode_object(self, tmp_path):
        """DriftDetector accepts a DecisionEpisode directly."""
        detector = DriftDetector(canon_path=tmp_path / "mg" / "memory_graph.jsonl")
        episode = _make_episode()
        signals = detector.detect_from_episode(episode)
        assert signals == []

    def test_detect_from_claims(self, tmp_path):
        """detect_from_claims works with pre-extracted items."""
        from dashboard.server.models_exhaust import TruthItem

        detector = DriftDetector(canon_path=tmp_path / "nonexistent.jsonl")
        signals = detector.detect_from_claims(
            truth=[TruthItem(claim="x", evidence="y", confidence=0.9)],
            memory=[],
            episode_id="ep-1",
        )
        assert isinstance(signals, list)

    def test_backward_compat_import(self):
        """exhaust_refiner.detect_drift still importable."""
        from engine.exhaust_refiner import detect_drift
        assert callable(detect_drift)
