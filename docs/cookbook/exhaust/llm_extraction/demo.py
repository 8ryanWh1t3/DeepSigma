#!/usr/bin/env python3
"""
cookbook/exhaust/llm_extraction/demo.py
========================================
Demonstrates LLM-backed extraction on a sample episode.

Prerequisites:
    pip install -e ".[exhaust-llm]"
    export ANTHROPIC_API_KEY="sk-ant-..."
    export EXHAUST_USE_LLM="1"   # optional — demo calls LLMExtractor directly

Run from repo root:
    python cookbook/exhaust/llm_extraction/demo.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from dashboard.server.models_exhaust import DecisionEpisode, EpisodeEvent, Source
from engine.exhaust_refiner import refine_episode


# ── Build a realistic sample episode ─────────────────────────────────────────

def _make_demo_episode() -> DecisionEpisode:
    events = [
        EpisodeEvent(
            event_id="ev-demo-01",
            episode_id="ep-demo-001",
            event_type="prompt",
            timestamp="2026-02-17T14:00:00Z",
            source="manual",
            user_hash="u_demo",
            session_id="sess-demo",
            project="acme-rag",
            team="ml-ops",
            payload={"text": "What is the current deployment status of service-alpha?", "role": "user"},
        ),
        EpisodeEvent(
            event_id="ev-demo-02",
            episode_id="ep-demo-001",
            event_type="tool",
            timestamp="2026-02-17T14:00:01Z",
            source="manual",
            user_hash="u_demo",
            session_id="sess-demo",
            project="acme-rag",
            team="ml-ops",
            payload={"name": "check_deployment", "arguments": {"service": "service-alpha"}},
        ),
        EpisodeEvent(
            event_id="ev-demo-03",
            episode_id="ep-demo-001",
            event_type="tool",
            timestamp="2026-02-17T14:00:02Z",
            source="manual",
            user_hash="u_demo",
            session_id="sess-demo",
            project="acme-rag",
            team="ml-ops",
            payload={"status": "healthy", "version": "2.4.1", "replicas": 3},
        ),
        EpisodeEvent(
            event_id="ev-demo-04",
            episode_id="ep-demo-001",
            event_type="completion",
            timestamp="2026-02-17T14:00:03Z",
            source="manual",
            user_hash="u_demo",
            session_id="sess-demo",
            project="acme-rag",
            team="ml-ops",
            payload={
                "text": (
                    "Service-alpha is healthy, running version 2.4.1 with 3 replicas. "
                    "Last deployed today at 10:30 UTC. I recommend monitoring for 30 minutes "
                    "before any rollback decision."
                ),
                "role": "assistant",
                "model": "claude-haiku-4-5-20251001",
            },
        ),
        EpisodeEvent(
            event_id="ev-demo-05",
            episode_id="ep-demo-001",
            event_type="metric",
            timestamp="2026-02-17T14:00:04Z",
            source="manual",
            user_hash="u_demo",
            session_id="sess-demo",
            project="acme-rag",
            team="ml-ops",
            payload={"name": "latency_ms", "value": 1240, "unit": "ms"},
        ),
    ]
    return DecisionEpisode(
        episode_id="ep-demo-001",
        events=events,
        source=Source.manual,
        user_hash="u_demo",
        session_id="sess-demo",
        project="acme-rag",
        team="ml-ops",
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Exhaust LLM Extraction Demo ===")

    episode = _make_demo_episode()
    print(f"Episode: {episode.episode_id}  ({len(episode.events)} events)")
    print()

    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_llm:
        print("Refining with LLM extraction (claude-haiku-4-5-20251001)...")
    else:
        print("ANTHROPIC_API_KEY not set — using rule-based extraction.")
        print("Set ANTHROPIC_API_KEY to enable LLM extraction.")
    print()

    # Use LLMExtractor directly if key is available (works even without PR #2)
    if use_llm:
        try:
            from engine.exhaust_llm_extractor import LLMExtractor
            buckets = LLMExtractor().extract(episode)
            print(f"Truth items (LLM):     {len(buckets['truth'])}")
            for t in buckets["truth"][:5]:
                print(f"  [{t.confidence:.2f}] {t.claim[:80]}")
            print(f"Reasoning items (LLM): {len(buckets['reasoning'])}")
            for r in buckets["reasoning"][:3]:
                print(f"  [{r.confidence:.2f}] {r.decision[:80]}")
            print(f"Memory items (LLM):    {len(buckets['memory'])}")
            for m in buckets["memory"][:5]:
                print(f"  {m.entity} ({m.artifact_type})")
            print()
        except Exception as exc:
            print(f"LLM extraction failed: {exc}")
            use_llm = False

    print("Running full pipeline (rule-based)...")
    refined = refine_episode(episode)

    print("--- Results ---")
    print(f"Grade:           {refined.grade.value}")
    print(f"Coherence score: {refined.coherence_score}")
    print(f"Truth items:     {len(refined.truth)}")
    for t in refined.truth[:5]:
        print(f"  [{t.confidence:.2f}] {t.claim[:80]}")

    print(f"Reasoning items: {len(refined.reasoning)}")
    for r in refined.reasoning[:3]:
        print(f"  [{r.confidence:.2f}] {r.decision[:80]}")

    print(f"Memory items:    {len(refined.memory)}")
    for m in refined.memory[:5]:
        print(f"  {m.entity} ({m.artifact_type})")

    if refined.drift_signals:
        print(f"Drift signals:   {len(refined.drift_signals)}")
        for d in refined.drift_signals:
            print(f"  [{d.severity.value}] {d.drift_type.value}: {d.description[:60]}")

    print()
    print("=== Done ===")


if __name__ == "__main__":
    main()
