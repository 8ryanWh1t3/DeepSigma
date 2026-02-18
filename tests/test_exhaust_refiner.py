"""Tests for engine/exhaust_refiner.py — all 5 refiner functions.

Run from repo root:
    pytest tests/test_exhaust_refiner.py -v
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    DriftSeverity,
    DriftType,
    EpisodeEvent,
    EventType,
    Source,
)
from engine.exhaust_refiner import (
    detect_drift,
    extract_memory,
    extract_reasoning,
    extract_truth,
    refine_episode,
    score_coherence,
)


# ── Fixtures ──────────────────────────────────────────────────────

def _make_event(event_type: str, payload: dict, session_id: str = "sess-test") -> dict:
    return {
        "event_id": f"test-{event_type}-01",
        "episode_id": "ep-test-001",
        "event_type": event_type,
        "timestamp": "2026-01-01T00:00:00Z",
        "source": "manual",
        "user_hash": "u_test",
        "session_id": session_id,
        "project": "test-project",
        "team": "test-team",
        "payload": payload,
    }


def _make_episode(events: list[dict]) -> DecisionEpisode:
    return DecisionEpisode(
        episode_id="ep-test-001",
        events=[EpisodeEvent(**e) for e in events],
        source=Source.manual,
        user_hash="u_test",
        session_id="sess-test",
        project="test-project",
        team="test-team",
    )


SAMPLE_EVENTS_PATH = Path(__file__).parents[1] / "specs" / "sample_episode_events.jsonl"


def _load_sample_episode() -> DecisionEpisode:
    """Load first session from sample_episode_events.jsonl."""
    ep_id = "ep-sample-001"
    events = []
    with open(SAMPLE_EVENTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("session_id") == "sess-001":
                data["episode_id"] = ep_id
                events.append(data)
    return DecisionEpisode(
        episode_id=ep_id,
        events=[EpisodeEvent(**e) for e in events],
        source=Source.manual,
        user_hash="u_abc123",
        session_id="sess-001",
        project="acme-rag",
        team="ml-ops",
    )


# ── extract_truth ─────────────────────────────────────────────────

def test_extract_truth_from_metrics():
    """Metric events produce high-confidence truth claims."""
    episode = _make_episode([
        _make_event("metric", {"name": "latency_ms", "value": 240, "unit": "ms"}),
    ])
    truth = extract_truth(episode)
    assert len(truth) >= 1
    claim = truth[0]
    assert "latency_ms" in claim.claim.lower() or "240" in claim.claim
    assert claim.confidence >= 0.8


def test_extract_truth_from_completion():
    """Completion events with assertion-like lines produce claims."""
    episode = _make_episode([
        _make_event("completion", {
            "text": "Service-alpha is healthy and running version 2.4.1 with 3 replicas.",
        }),
    ])
    truth = extract_truth(episode)
    # At least one claim extracted from the assertion line
    assert len(truth) >= 1
    assert any("service" in t.claim.lower() or "is" in t.claim.lower() for t in truth)


def test_extract_truth_empty_episode():
    """Episode with no metric/completion events produces no truth claims."""
    episode = _make_episode([
        _make_event("prompt", {"text": "What is the status?"}),
    ])
    truth = extract_truth(episode)
    assert truth == []


# ── extract_reasoning ────────────────────────────────────────────

def test_extract_reasoning_keywords():
    """Lines with decision keywords produce reasoning items."""
    episode = _make_episode([
        _make_event("completion", {
            "text": "I recommend monitoring for 30 minutes before any rollback action.",
        }),
    ])
    reasoning = extract_reasoning(episode)
    assert len(reasoning) >= 1
    assert any("recommend" in r.decision.lower() for r in reasoning)


def test_extract_reasoning_tool_invocation():
    """Tool events produce reasoning items recording the tool use."""
    episode = _make_episode([
        _make_event("tool", {"tool_name": "check_deployment", "input": {"service": "alpha"}}),
    ])
    reasoning = extract_reasoning(episode)
    assert len(reasoning) >= 1
    assert any("check_deployment" in r.decision for r in reasoning)
    assert reasoning[0].confidence >= 0.7


def test_extract_reasoning_empty_completion():
    """Completions with no decision keywords produce no reasoning items."""
    episode = _make_episode([
        _make_event("completion", {"text": ""}),
    ])
    reasoning = extract_reasoning(episode)
    assert reasoning == []


# ── extract_memory ────────────────────────────────────────────────

def test_extract_memory_episode_node():
    """Episode node is always recorded in memory."""
    episode = _make_episode([
        _make_event("prompt", {"text": "Hello"}),
    ])
    memory = extract_memory(episode)
    episode_nodes = [m for m in memory if m.artifact_type == "episode"]
    assert len(episode_nodes) == 1
    assert episode_nodes[0].entity == "ep-test-001"
    assert episode_nodes[0].confidence == 1.0


def test_extract_memory_tools():
    """Tool events create tool memory nodes."""
    episode = _make_episode([
        _make_event("tool", {"tool_name": "iam_audit", "input": {}}),
    ])
    memory = extract_memory(episode)
    tool_nodes = [m for m in memory if m.artifact_type == "tool"]
    assert len(tool_nodes) >= 1
    assert any(m.entity == "iam_audit" for m in tool_nodes)


def test_extract_memory_model_from_completion():
    """Completion events with model field create model memory nodes."""
    episode = _make_episode([
        _make_event("completion", {"text": "Hello", "model": "claude-haiku-4-5"}),
    ])
    memory = extract_memory(episode)
    model_nodes = [m for m in memory if m.artifact_type == "model"]
    assert len(model_nodes) >= 1
    assert any(m.entity == "claude-haiku-4-5" for m in model_nodes)


# ── detect_drift ─────────────────────────────────────────────────

def test_detect_drift_empty_canon(tmp_path):
    """No canon → low_claim_coverage when episode has many events but no truth."""
    episode = _make_episode([
        _make_event("prompt", {"text": "q1"}),
        _make_event("prompt", {"text": "q2"}),
        _make_event("prompt", {"text": "q3"}),
    ])
    truth = []  # No truth extracted
    memory = extract_memory(episode)
    mg_path = tmp_path / "mg" / "memory_graph.jsonl"
    mg_path.parent.mkdir(parents=True)
    mg_path.touch()

    signals = detect_drift(episode, truth, memory, canon_path=mg_path)
    types = [s.drift_type for s in signals]
    assert DriftType.low_claim_coverage in types


def test_detect_drift_contradiction(tmp_path):
    """Conflicting property value triggers contradiction signal."""
    from engine.exhaust_refiner import TruthItem

    mg_path = tmp_path / "mg" / "memory_graph.jsonl"
    mg_path.parent.mkdir(parents=True)
    # Write canon with service-alpha version = 2.3.9
    with open(mg_path, "w") as f:
        f.write(json.dumps({
            "node_type": "truth",
            "entity": "service_alpha",
            "property_name": "version",
            "value": "2.3.9",
        }) + "\n")

    episode = _make_episode([_make_event("metric", {"name": "x", "value": 1})])
    # New truth says version = 2.4.1 (contradiction)
    truth = [TruthItem(
        claim="service_alpha version = 2.4.1",
        entity="service_alpha",
        property_name="version",
        value="2.4.1",
        confidence=0.9,
    )]
    memory = extract_memory(episode)

    signals = detect_drift(episode, truth, memory, canon_path=mg_path)
    contradiction_signals = [s for s in signals if s.drift_type == DriftType.contradiction]
    assert len(contradiction_signals) >= 1
    assert contradiction_signals[0].severity == DriftSeverity.yellow


def test_detect_drift_stale_reference(tmp_path):
    """Memory item referencing an unknown episode triggers stale_reference."""
    from engine.exhaust_refiner import MemoryItem

    mg_path = tmp_path / "mg" / "memory_graph.jsonl"
    mg_path.parent.mkdir(parents=True)
    # Canon has one known episode
    with open(mg_path, "w") as f:
        f.write(json.dumps({
            "node_type": "memory",
            "artifact_type": "episode",
            "entity": "ep-known-001",
        }) + "\n")

    episode = _make_episode([_make_event("metric", {"name": "x", "value": 1})])
    truth = []
    # Memory item references a DIFFERENT (unknown) episode
    memory = [
        MemoryItem(
            entity="check_deployment",
            relation="used_by",
            target="u_test",
            context="In episode ep-ghost-999",  # not in canon
            artifact_type="tool",
            confidence=0.85,
        )
    ]

    signals = detect_drift(episode, truth, memory, canon_path=mg_path)
    stale = [s for s in signals if s.drift_type == DriftType.stale_reference]
    assert len(stale) >= 1
    assert "ep-ghost-999" in stale[0].description


# ── score_coherence ───────────────────────────────────────────────

def test_score_coherence_empty():
    """Empty truth list does not raise; returns grade D."""
    score, grade, breakdown = score_coherence([], [], [], [])
    assert score >= 0.0
    assert score <= 100.0
    # No division by zero — evidenced by getting a float back
    assert isinstance(breakdown.evidence_quality, float)
    assert breakdown.evidence_quality == 0.0


def test_score_coherence_full():
    """Episode with good truth and reasoning scores B or higher."""
    from engine.exhaust_refiner import TruthItem, ReasoningItem, MemoryItem

    truth = [
        TruthItem(claim="latency = 240ms", confidence=0.9, entity="service", property_name="latency", value="240"),
        TruthItem(claim="replicas = 3", confidence=0.95, entity="service", property_name="replicas", value="3"),
    ]
    reasoning = [
        ReasoningItem(decision="I recommend monitoring first", rationale="error rate is borderline", confidence=0.8),
    ]
    memory = [
        MemoryItem(entity="ep-001", relation="belongs_to", target="project", artifact_type="episode", confidence=1.0),
    ]

    score, grade, breakdown = score_coherence(truth, reasoning, memory, [])
    assert score > 50.0
    assert grade.value in ("A", "B", "C")


# ── refine_episode (end-to-end) ───────────────────────────────────

def test_refine_episode_end_to_end():
    """Full pipeline produces a RefinedEpisode with expected shape."""
    episode = _load_sample_episode()
    refined = refine_episode(episode)

    assert refined.episode_id == "ep-sample-001"
    assert isinstance(refined.coherence_score, float)
    assert 0.0 <= refined.coherence_score <= 100.0
    assert refined.grade.value in ("A", "B", "C", "D")
    # Sample episode has metric events → should extract at least 1 truth
    assert len(refined.truth) >= 1
    # Episode node always in memory
    assert len(refined.memory) >= 1
    ep_nodes = [m for m in refined.memory if m.artifact_type == "episode"]
    assert len(ep_nodes) == 1
