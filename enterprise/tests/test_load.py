"""Load test — 100-episode corpus through the full coherence pipeline.

Verifies correctness and timing under load. IRIS SLO: < 60s.
"""

import time

import pytest


class TestFullPipelineLoad:
    """Run 100 episodes through the complete pipeline."""

    @pytest.fixture
    def corpus_100(self, minimal_episode, minimal_drift):
        """Generate a 100-episode corpus with associated drift events."""
        episodes = []
        drifts = []
        outcomes = ["success", "success", "success", "partial", "fail"]
        drift_types = ["freshness", "verify", "outcome"]
        severities = ["green", "yellow", "red"]

        for i in range(100):
            ep = minimal_episode(
                episode_id=f"ep-load-{i:03d}",
                decision_type="AccountQuarantine",
                outcome={"code": outcomes[i % len(outcomes)]},
                telemetry={
                    "endToEndMs": 50 + (i % 50),
                    "stageMs": {"context": 15, "plan": 15, "act": 10, "verify": 10},
                    "p95Ms": 100, "p99Ms": 120, "jitterMs": i % 10,
                    "fallbackUsed": False, "fallbackStep": "none",
                    "hopCount": 1, "fanout": 1,
                },
            )
            episodes.append(ep)

            # 30% of episodes get a drift event
            if i % 3 == 0:
                d = minimal_drift(
                    drift_id=f"drift-load-{i:03d}",
                    episode_id=f"ep-load-{i:03d}",
                    driftType=drift_types[i % len(drift_types)],
                    severity=severities[i % len(severities)],
                )
                drifts.append(d)

        return episodes, drifts

    def test_pipeline_correctness(self, corpus_100):
        """All 100 episodes ingest correctly and produce valid artifacts."""
        from core import (
            CoherenceScorer,
            DLRBuilder,
            DriftSignalCollector,
            MemoryGraph,
            ReflectionSession,
        )

        episodes, drifts = corpus_100

        dlr = DLRBuilder()
        dlr.from_episodes(episodes)

        rs = ReflectionSession("load-test-rs")
        rs.ingest(episodes)

        ds = DriftSignalCollector()
        ds.ingest(drifts)

        mg = MemoryGraph()
        for ep in episodes:
            mg.add_episode(ep)
        for d in drifts:
            mg.add_drift(d)

        # Verify artifact counts
        assert len(dlr.to_dict_list()) >= 100
        summary = rs.summarise()
        assert summary.episode_count >= 100
        assert mg.node_count >= 100

        # Scoring should succeed
        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()
        assert report.overall_score >= 0
        assert report.grade in ("A", "B", "C", "D")

    def test_iris_query_under_slo(self, corpus_100):
        """IRIS queries on 100-episode corpus complete within 60s SLO."""
        from core import (
            DLRBuilder,
            DriftSignalCollector,
            IRISConfig,
            IRISEngine,
            IRISQuery,
            MemoryGraph,
            ReflectionSession,
        )

        episodes, drifts = corpus_100

        dlr = DLRBuilder()
        dlr.from_episodes(episodes)
        rs = ReflectionSession("load-test-rs")
        rs.ingest(episodes)
        ds = DriftSignalCollector()
        ds.ingest(drifts)
        mg = MemoryGraph()
        for ep in episodes:
            mg.add_episode(ep)
        for d in drifts:
            mg.add_drift(d)

        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )

        # Run all 5 query types
        query_types = ["WHY", "WHAT_CHANGED", "WHAT_DRIFTED", "RECALL", "STATUS"]
        total_start = time.monotonic()

        for qt in query_types:
            query = IRISQuery(
                query_type=qt,
                episode_id="ep-load-050" if qt != "STATUS" else "",
            )
            response = engine.resolve(query)
            assert response.status in ("RESOLVED", "PARTIAL", "NOT_FOUND")

        total_elapsed = time.monotonic() - total_start
        assert total_elapsed < 60, f"IRIS queries took {total_elapsed:.1f}s (SLO: 60s)"

    def test_mg_traversal_at_scale(self, corpus_100):
        """MG traversal queries work correctly at 100-episode scale."""
        from core import MemoryGraph

        episodes, drifts = corpus_100

        mg = MemoryGraph()
        for ep in episodes:
            mg.add_episode(ep)
        for d in drifts:
            mg.add_drift(d)

        # stats query should include all nodes
        stats = mg.query("stats")
        assert stats["total_nodes"] >= 100

        # why query for a specific episode
        result = mg.query("why", episode_id="ep-load-050")
        assert isinstance(result, dict)

        # drift query
        result = mg.query("drift", episode_id="ep-load-000")
        assert isinstance(result, dict)
