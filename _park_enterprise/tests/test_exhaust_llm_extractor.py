"""Tests for engine/exhaust_llm_extractor.py — all mocked, no API key needed.

Run from repo root:
    pytest tests/test_exhaust_llm_extractor.py -v
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    EpisodeEvent,
    Source,
)
from engine.exhaust_llm_extractor import LLMExtractor, _MAX_PROMPT_CHARS


# ── Fixtures ──────────────────────────────────────────────────────

def _make_episode(n_events: int = 2) -> DecisionEpisode:
    events = [
        EpisodeEvent(
            event_id=f"ev-{i:02d}",
            episode_id="ep-llm-test",
            event_type="metric",
            timestamp="2026-01-01T00:00:00Z",
            source="manual",
            payload={"name": "latency_ms", "value": 240 + i},
        )
        for i in range(n_events)
    ]
    return DecisionEpisode(
        episode_id="ep-llm-test",
        events=events,
        source=Source.manual,
        user_hash="u_test",
        session_id="sess-test",
        project="test-project",
        team="test-team",
    )


def _good_llm_response() -> str:
    return json.dumps({
        "truth": [
            {"claim": "latency = 240ms", "confidence": 0.92, "evidence": "metric event"},
        ],
        "reasoning": [
            {"decision": "I recommend rollback", "confidence": 0.8, "rationale": "error rate high"},
        ],
        "memory": [
            {"entity": "service-alpha", "entity_type": "service",
             "relations": ["monitored"], "confidence": 0.9},
        ],
    })


def _mock_message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


# ── Tests ─────────────────────────────────────────────────────────

def test_extract_returns_valid_buckets(monkeypatch):
    """Happy path — LLM JSON response is parsed into typed bucket objects."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    with patch("engine.exhaust_llm_extractor.LLMExtractor._call_api",
               return_value=_good_llm_response()):
        buckets = LLMExtractor().extract(_make_episode())

    assert len(buckets["truth"]) == 1
    assert buckets["truth"][0].claim == "latency = 240ms"
    assert buckets["truth"][0].confidence == pytest.approx(0.92)

    assert len(buckets["reasoning"]) == 1
    assert "rollback" in buckets["reasoning"][0].decision.lower()

    assert len(buckets["memory"]) == 1
    assert buckets["memory"][0].entity == "service-alpha"


def test_extract_fallback_on_api_error(monkeypatch):
    """API raises → empty buckets returned, no exception propagates."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    with patch("engine.exhaust_llm_extractor.LLMExtractor._call_api",
               side_effect=ConnectionError("network down")):
        buckets = LLMExtractor().extract(_make_episode())

    assert buckets["truth"] == []
    assert buckets["reasoning"] == []
    assert buckets["memory"] == []


def test_extract_fallback_on_bad_json(monkeypatch):
    """LLM returns non-JSON text → empty buckets, no crash."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    with patch("engine.exhaust_llm_extractor.LLMExtractor._call_api",
               return_value="Sorry, I cannot help with that."):
        buckets = LLMExtractor().extract(_make_episode())

    assert buckets["truth"] == []
    assert buckets["reasoning"] == []
    assert buckets["memory"] == []


def test_build_prompt_truncates_long_episode(monkeypatch):
    """Episode transcript longer than _MAX_PROMPT_CHARS is truncated, not dropped."""
    # Create episode with many large events
    events = [
        EpisodeEvent(
            event_id=f"ev-{i:03d}",
            episode_id="ep-long",
            event_type="completion",
            timestamp="2026-01-01T00:00:00Z",
            source="manual",
            payload={"text": "x" * 500},
        )
        for i in range(30)
    ]
    episode = DecisionEpisode(
        episode_id="ep-long",
        events=events,
        source=Source.manual,
        user_hash="u_test",
        session_id="sess-long",
        project="test",
        team="test",
    )

    extractor = LLMExtractor()
    prompt = extractor._build_prompt(episode)

    assert len(prompt) <= _MAX_PROMPT_CHARS + 100  # small buffer for suffix
    assert "...(truncated)" in prompt
    assert "ep-long" in prompt  # episode ID always present


def test_confidence_clamped_0_to_1(monkeypatch):
    """LLM returning confidence > 1.0 or < 0.0 is clamped to valid range."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    bad_response = json.dumps({
        "truth": [
            {"claim": "x > 0", "confidence": 1.5, "evidence": "test"},
            {"claim": "y < 0", "confidence": -0.3, "evidence": "test"},
        ],
        "reasoning": [],
        "memory": [],
    })

    with patch("engine.exhaust_llm_extractor.LLMExtractor._call_api",
               return_value=bad_response):
        buckets = LLMExtractor().extract(_make_episode())

    confidences = [t.confidence for t in buckets["truth"]]
    assert all(0.0 <= c <= 1.0 for c in confidences), f"Out-of-range: {confidences}"
    assert confidences[0] == pytest.approx(1.0)  # 1.5 → clamped to 1.0
    assert confidences[1] == pytest.approx(0.0)  # -0.3 → clamped to 0.0
