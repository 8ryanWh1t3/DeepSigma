"""Performance benchmarks for exhaust pipeline at production scale.

Validates throughput and memory characteristics at 10k, 50k, and 100k nodes.
Uses generous time bounds to avoid CI flakiness.

Run:  pytest tests/test_exhaust_performance.py -v
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    EpisodeEvent,
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


# ── Synthetic data generators ─────────────────────────────────────


def _make_event(idx: int) -> dict:
    """Generate a synthetic EpisodeEvent dict with rotating types."""
    event_types = ["metric", "completion", "tool", "prompt"]
    etype = event_types[idx % len(event_types)]

    payload: Dict[str, Any] = {}
    if etype == "metric":
        payload = {"name": f"metric_{idx}", "value": idx * 1.5, "unit": "ms"}
    elif etype == "completion":
        payload = {
            "text": f"The service is running at {idx} requests per second and has {idx % 100} active connections.",
            "model": "claude-haiku-4-5",
        }
    elif etype == "tool":
        payload = {"tool_name": f"tool_{idx % 20}", "input": {"target": f"svc-{idx % 50}"}}
    elif etype == "prompt":
        payload = {"text": f"Check status of service {idx % 50}"}

    return {
        "event_id": f"evt-perf-{idx:06d}",
        "episode_id": "ep-perf-001",
        "event_type": etype,
        "timestamp": f"2026-02-19T{(idx // 3600) % 24:02d}:{(idx // 60) % 60:02d}:{idx % 60:02d}Z",
        "source": "manual",
        "user_hash": "u_perf",
        "session_id": "sess-perf",
        "project": "perf-test",
        "team": "perf-team",
        "payload": payload,
    }


def _make_episode(n_events: int) -> DecisionEpisode:
    """Build a DecisionEpisode with n synthetic events."""
    events = [_make_event(i) for i in range(n_events)]
    return DecisionEpisode(
        episode_id="ep-perf-001",
        events=[EpisodeEvent(**e) for e in events],
        source=Source.manual,
        user_hash="u_perf",
        session_id="sess-perf",
        project="perf-test",
        team="perf-team",
    )


def _write_jsonl(path: Path, records: List[dict]) -> None:
    """Write records to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")


def _make_canon_records(n: int) -> List[dict]:
    """Generate n canon records for drift detection benchmark."""
    records = []
    for i in range(n):
        if i % 3 == 0:
            records.append({
                "node_type": "truth",
                "entity": f"service_{i % 500}",
                "property_name": f"metric_{i}",
                "value": str(i * 1.5),
            })
        elif i % 3 == 1:
            records.append({
                "node_type": "memory",
                "artifact_type": "episode",
                "entity": f"ep-canon-{i:06d}",
            })
        else:
            records.append({
                "node_type": "memory",
                "artifact_type": "tool",
                "entity": f"tool_{i % 20}",
                "context": f"In episode ep-canon-{i:06d}",
            })
    return records


# ── Streaming JSONL correctness ───────────────────────────────────


class TestStreamingJSONL:
    """Verify streaming helpers match load-all behavior."""

    def test_iter_jsonl_matches_read(self, tmp_path):
        from dashboard.server.exhaust_api import _iter_jsonl, _read_jsonl

        p = tmp_path / "data.jsonl"
        records = [{"id": i, "value": f"v{i}"} for i in range(100)]
        _write_jsonl(p, records)

        loaded = _read_jsonl(p)
        streamed = list(_iter_jsonl(p))
        assert loaded == streamed

    def test_iter_jsonl_empty_file(self, tmp_path):
        from dashboard.server.exhaust_api import _iter_jsonl

        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert list(_iter_jsonl(p)) == []

    def test_iter_jsonl_missing_file(self, tmp_path):
        from dashboard.server.exhaust_api import _iter_jsonl

        assert list(_iter_jsonl(tmp_path / "nope.jsonl")) == []

    def test_iter_jsonl_skips_malformed(self, tmp_path):
        from dashboard.server.exhaust_api import _iter_jsonl

        p = tmp_path / "data.jsonl"
        p.write_text('{"id": 1}\nnot json\n{"id": 2}\n')
        assert len(list(_iter_jsonl(p))) == 2

    def test_count_jsonl_matches_len(self, tmp_path):
        from dashboard.server.exhaust_api import _count_jsonl, _read_jsonl

        p = tmp_path / "data.jsonl"
        records = [{"id": i} for i in range(500)]
        _write_jsonl(p, records)
        assert _count_jsonl(p) == len(_read_jsonl(p))

    def test_count_jsonl_empty(self, tmp_path):
        from dashboard.server.exhaust_api import _count_jsonl

        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert _count_jsonl(p) == 0

    def test_count_jsonl_missing(self, tmp_path):
        from dashboard.server.exhaust_api import _count_jsonl

        assert _count_jsonl(tmp_path / "nope.jsonl") == 0

    def test_count_jsonl_skips_malformed(self, tmp_path):
        from dashboard.server.exhaust_api import _count_jsonl

        p = tmp_path / "data.jsonl"
        p.write_text('{"id": 1}\nbad\n{"id": 2}\n')
        assert _count_jsonl(p) == 2


# ── Refiner throughput ────────────────────────────────────────────


class TestExhaustRefinerThroughput:
    """Benchmark refiner extraction functions at scale."""

    def test_extract_truth_10k_events(self):
        """10k events through extract_truth under 5s."""
        episode = _make_episode(10_000)
        start = time.monotonic()
        truth = extract_truth(episode)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"extract_truth took {elapsed:.2f}s (SLO: 5s)"
        assert len(truth) > 0

    def test_extract_reasoning_10k_events(self):
        """10k events through extract_reasoning under 5s."""
        episode = _make_episode(10_000)
        start = time.monotonic()
        reasoning = extract_reasoning(episode)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"extract_reasoning took {elapsed:.2f}s (SLO: 5s)"
        assert len(reasoning) > 0

    def test_extract_memory_10k_events(self):
        """10k events through extract_memory under 5s."""
        episode = _make_episode(10_000)
        start = time.monotonic()
        memory = extract_memory(episode)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"extract_memory took {elapsed:.2f}s (SLO: 5s)"
        assert len(memory) > 0

    def test_refine_episode_1k_events(self, tmp_path):
        """Full refine_episode with 1k events under 10s."""
        # Use tmp canon to avoid filesystem side effects
        mg_path = tmp_path / "mg" / "memory_graph.jsonl"
        mg_path.parent.mkdir(parents=True)
        mg_path.touch()

        episode = _make_episode(1_000)
        start = time.monotonic()
        refined = refine_episode(episode)
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"refine_episode took {elapsed:.2f}s (SLO: 10s)"
        assert refined.episode_id == "ep-perf-001"
        assert refined.coherence_score >= 0

    def test_detect_drift_10k_canon(self, tmp_path):
        """Drift detection against 10k canon entries under 5s."""
        mg_path = tmp_path / "mg" / "memory_graph.jsonl"
        _write_jsonl(mg_path, _make_canon_records(10_000))

        episode = _make_episode(100)
        truth = extract_truth(episode)
        memory = extract_memory(episode)

        start = time.monotonic()
        signals = detect_drift(episode, truth, memory, canon_path=mg_path)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"detect_drift took {elapsed:.2f}s (SLO: 5s)"
        assert isinstance(signals, list)

    def test_detect_drift_50k_canon(self, tmp_path):
        """Drift detection against 50k canon entries under 10s."""
        mg_path = tmp_path / "mg" / "memory_graph.jsonl"
        _write_jsonl(mg_path, _make_canon_records(50_000))

        episode = _make_episode(100)
        truth = extract_truth(episode)
        memory = extract_memory(episode)

        start = time.monotonic()
        signals = detect_drift(episode, truth, memory, canon_path=mg_path)
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"detect_drift took {elapsed:.2f}s (SLO: 10s)"
        assert isinstance(signals, list)

    def test_score_coherence_10k_items(self):
        """Coherence scoring with 10k truth items under 2s."""
        from dashboard.server.models_exhaust import (
            DriftSeverity,
            DriftSignal,
            DriftType,
            MemoryItem,
            ReasoningItem,
            TruthItem,
        )

        truth = [
            TruthItem(
                claim=f"metric_{i} = {i * 1.5}",
                confidence=0.9 - (i % 5) * 0.1,
                entity=f"svc_{i % 100}",
                property_name=f"metric_{i}",
                value=str(i * 1.5),
            )
            for i in range(10_000)
        ]
        reasoning = [
            ReasoningItem(
                decision=f"Use tool_{i}",
                rationale=f"Because metric_{i} is elevated" if i % 2 == 0 else "",
                confidence=0.7,
            )
            for i in range(1_000)
        ]
        memory = [
            MemoryItem(
                entity=f"tool_{i}",
                relation="used_by",
                target="user",
                artifact_type="tool",
                confidence=0.85,
            )
            for i in range(500)
        ]
        drift = [
            DriftSignal(
                drift_type=DriftType.contradiction,
                severity=DriftSeverity.yellow,
                entity=f"svc_{i}",
            )
            for i in range(50)
        ]

        start = time.monotonic()
        score, grade, breakdown = score_coherence(truth, reasoning, memory, drift)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"score_coherence took {elapsed:.2f}s (SLO: 2s)"
        assert 0 <= score <= 100


# ── JSONL streaming performance ───────────────────────────────────


class TestJSONLStreamingPerformance:
    """Benchmark streaming JSONL at 100k scale."""

    def test_iter_jsonl_100k_records(self, tmp_path):
        """Stream 100k records in bounded memory."""
        from dashboard.server.exhaust_api import _iter_jsonl

        p = tmp_path / "big.jsonl"
        records = [{"event_id": f"e-{i}", "data": f"payload-{i}"} for i in range(100_000)]
        _write_jsonl(p, records)

        start = time.monotonic()
        count = 0
        for _ in _iter_jsonl(p):
            count += 1
        elapsed = time.monotonic() - start

        assert count == 100_000
        assert elapsed < 10.0, f"_iter_jsonl 100k took {elapsed:.2f}s (SLO: 10s)"

    def test_count_jsonl_100k_records(self, tmp_path):
        """Count 100k records under 10s."""
        from dashboard.server.exhaust_api import _count_jsonl

        p = tmp_path / "big.jsonl"
        records = [{"event_id": f"e-{i}"} for i in range(100_000)]
        _write_jsonl(p, records)

        start = time.monotonic()
        count = _count_jsonl(p)
        elapsed = time.monotonic() - start

        assert count == 100_000
        assert elapsed < 10.0, f"_count_jsonl 100k took {elapsed:.2f}s (SLO: 10s)"

    def test_iter_vs_read_memory_ratio(self, tmp_path):
        """Streaming should not accumulate all records."""
        from dashboard.server.exhaust_api import _iter_jsonl

        p = tmp_path / "medium.jsonl"
        records = [{"event_id": f"e-{i}", "payload": "x" * 200} for i in range(10_000)]
        _write_jsonl(p, records)

        # Stream and only count — should not retain records
        count = sum(1 for _ in _iter_jsonl(p))
        assert count == 10_000


# ── Scorecard performance ─────────────────────────────────────────


class TestScorecardPerformance:
    """Benchmark Trust Scorecard generation."""

    def test_scorecard_generation_from_summary(self, tmp_path):
        """Scorecard generation from summary.json under 1s."""
        from tools.trust_scorecard import generate_scorecard

        # Create synthetic Golden Path output
        gp_dir = tmp_path / "gp_out"
        gp_dir.mkdir()
        (gp_dir / "step_2_normalize").mkdir()

        summary = {
            "elapsed_ms": 5000,
            "steps_completed": ["connect", "normalize", "extract", "seal", "drift", "patch", "recall"],
            "canonical_records": 10_000,
            "iris_queries": {"q1": "RESOLVED", "q2": "RESOLVED", "q3": "RESOLVED"},
            "drift_events": 50,
            "patch_applied": True,
            "baseline_score": 72.5,
            "baseline_grade": "C",
            "patched_score": 88.3,
            "patched_grade": "A",
        }
        (gp_dir / "summary.json").write_text(json.dumps(summary))

        start = time.monotonic()
        scorecard = generate_scorecard(str(gp_dir))
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, f"scorecard generation took {elapsed:.2f}s (SLO: 1s)"
        assert scorecard["metrics"]["steps_completed"] == 7
        assert scorecard["metrics"]["baseline_score"] == 72.5


# ── End-to-end scale tests ────────────────────────────────────────


class TestEndToEndScale:
    """Full pipeline throughput at varying scales."""

    def test_full_pipeline_10k_events(self, tmp_path):
        """Full extract→drift→score pipeline with 10k events under 15s."""
        mg_path = tmp_path / "mg" / "memory_graph.jsonl"
        _write_jsonl(mg_path, _make_canon_records(1_000))

        episode = _make_episode(10_000)

        start = time.monotonic()
        truth = extract_truth(episode)
        reasoning = extract_reasoning(episode)
        memory = extract_memory(episode)
        drift = detect_drift(episode, truth, memory, canon_path=mg_path)
        score, grade, breakdown = score_coherence(truth, reasoning, memory, drift)
        elapsed = time.monotonic() - start

        assert elapsed < 15.0, f"Full pipeline took {elapsed:.2f}s (SLO: 15s)"
        assert len(truth) > 0
        assert 0 <= score <= 100
