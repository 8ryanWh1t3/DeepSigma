"""Tests for the coherence metrics module."""

import json

import pytest

from core.metrics import MetricPoint, MetricsCollector, MetricsReport


# ── MetricPoint ──────────────────────────────────────────────────


class TestMetricPoint:
    def test_fields(self):
        mp = MetricPoint(name="test", value=42.0, unit="score")
        assert mp.name == "test"
        assert mp.value == 42.0
        assert mp.unit == "score"

    def test_details_default(self):
        mp = MetricPoint(name="test", value=0.0, unit="ratio")
        assert mp.details == {}


# ── MetricsReport ────────────────────────────────────────────────


class TestMetricsReport:
    def test_to_json(self):
        report = MetricsReport(
            computed_at="2026-02-27T10:00:00Z",
            metrics=[MetricPoint(name="x", value=1.0, unit="count")],
            summary={"x": 1.0},
        )
        raw = report.to_json()
        data = json.loads(raw)
        assert data["computed_at"] == "2026-02-27T10:00:00Z"
        assert len(data["metrics"]) == 1

    def test_summary_key_matches(self):
        report = MetricsReport(
            computed_at="now",
            metrics=[MetricPoint(name="a", value=2.0, unit="score")],
            summary={"a": 2.0},
        )
        assert report.summary["a"] == 2.0


# ── MetricsCollector ─────────────────────────────────────────────


class TestMetricsCollector:
    def test_collect_returns_4_metrics(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(
            dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        )
        report = collector.collect()
        assert len(report.metrics) == 4
        names = {m.name for m in report.metrics}
        assert names == {
            "coherence_score",
            "drift_density",
            "authority_coverage",
            "memory_coverage",
        }

    def test_coherence_score_range(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        score = next(m for m in report.metrics if m.name == "coherence_score")
        assert 0 <= score.value <= 100
        assert "grade" in score.details

    def test_drift_density_ratio(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        dd = next(m for m in report.metrics if m.name == "drift_density")
        assert dd.unit == "ratio"
        assert dd.value >= 0

    def test_memory_coverage_ratio(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        mc = next(m for m in report.metrics if m.name == "memory_coverage")
        assert mc.unit == "ratio"
        assert 0 <= mc.value <= 1.0

    def test_authority_coverage_no_ledger(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        ac = next(m for m in report.metrics if m.name == "authority_coverage")
        # Without a ledger, no claims are in MG (episodes only) so coverage=1.0
        # or if claims present, coverage=0.0
        assert ac.unit == "ratio"

    def test_authority_coverage_with_ledger(self, coherence_pipeline):
        from core.authority import AuthorityLedger, AuthorityEntry
        dlr, rs, ds, mg = coherence_pipeline
        ledger = AuthorityLedger()
        collector = MetricsCollector(
            dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
            authority_ledger=ledger,
        )
        report = collector.collect()
        ac = next(m for m in report.metrics if m.name == "authority_coverage")
        assert ac.unit == "ratio"

    def test_empty_pipeline(self):
        from core import DLRBuilder, DriftSignalCollector, MemoryGraph, ReflectionSession
        collector = MetricsCollector(
            dlr_builder=DLRBuilder(),
            rs=ReflectionSession("empty"),
            ds=DriftSignalCollector(),
            mg=MemoryGraph(),
        )
        report = collector.collect()
        assert len(report.metrics) == 4
        score = next(m for m in report.metrics if m.name == "coherence_score")
        assert score.value >= 0

    def test_summary_matches_metrics(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        for m in report.metrics:
            assert m.name in report.summary
            assert report.summary[m.name] == m.value

    def test_report_serializable(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        collector = MetricsCollector(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = collector.collect()
        raw = report.to_json()
        data = json.loads(raw)
        assert "metrics" in data
        assert "summary" in data
