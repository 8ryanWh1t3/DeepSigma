"""Performance benchmarks for critical DeepSigma operations.

Run:  pytest tests/test_benchmarks.py -v
Skip: pytest tests/ -v -m "not benchmark"
"""

import pytest

pytestmark = pytest.mark.benchmark

# Skip entire module if pytest-benchmark is not installed
pytest.importorskip("pytest_benchmark")


class TestIRISBenchmark:
    """Benchmark IRIS query resolution times."""

    def test_iris_why_query(self, benchmark, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        from core import IRISConfig, IRISEngine, IRISQuery

        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )
        query = IRISQuery(query_type="WHY", episode_id="ep-demo-001")
        result = benchmark(engine.resolve, query)
        assert result.status in ("RESOLVED", "PARTIAL")

    def test_iris_status_query(self, benchmark, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        from core import IRISConfig, IRISEngine, IRISQuery

        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )
        query = IRISQuery(query_type="STATUS")
        result = benchmark(engine.resolve, query)
        assert result.status in ("RESOLVED", "PARTIAL")

    def test_iris_what_drifted_query(self, benchmark, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        from core import IRISConfig, IRISEngine, IRISQuery

        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )
        query = IRISQuery(query_type="WHAT_DRIFTED")
        result = benchmark(engine.resolve, query)
        assert result.status in ("RESOLVED", "PARTIAL")


class TestCoherenceScorerBenchmark:
    """Benchmark coherence scoring pipeline."""

    def test_scoring(self, benchmark, coherence_pipeline):
        from core import CoherenceScorer

        dlr, rs, ds, mg = coherence_pipeline
        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = benchmark(scorer.score)
        assert report.overall_score >= 0


class TestMGTraversalBenchmark:
    """Benchmark Memory Graph operations at scale."""

    def test_mg_add_100_episodes(self, benchmark, minimal_episode):
        from core import MemoryGraph

        def run():
            mg = MemoryGraph()
            for i in range(100):
                mg.add_episode(minimal_episode(episode_id=f"ep-bench-{i:03d}"))
            return mg

        mg = benchmark(run)
        assert mg.node_count >= 100

    def test_mg_query_100_episodes(self, benchmark, minimal_episode):
        from core import MemoryGraph

        mg = MemoryGraph()
        for i in range(100):
            mg.add_episode(minimal_episode(episode_id=f"ep-bench-{i:03d}"))

        def run():
            for i in range(100):
                mg.query("why", episode_id=f"ep-bench-{i:03d}")

        benchmark(run)
        assert mg.node_count >= 100
