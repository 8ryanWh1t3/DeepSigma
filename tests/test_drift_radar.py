"""Tests for drift_radar package — models, adapter, runtime, analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.drift_radar.models import (
    DomainDriftView,
    DriftCorrelation,
    DriftForecast,
    DriftTrend,
    RadarSnapshot,
    RemediationPriority,
)
from core.drift_radar.radar_adapter import RadarAdapter
from core.drift_radar.inmemory_adapter import InMemoryRadarAdapter
from core.drift_radar.correlation import amplify_severity_score, find_correlations
from core.drift_radar.trending import compute_trends
from core.drift_radar.forecasting import project_drift
from core.drift_radar.prioritization import rank_remediations
from core.drift_radar.runtime import DriftRadar


# ── Model Tests ──────────────────────────────────────────────────


class TestModels:
    def test_domain_drift_view_defaults(self):
        view = DomainDriftView(domain="intelops")
        assert view.total_signals == 0
        assert view.worst_severity == "green"

    def test_radar_snapshot_defaults(self):
        snap = RadarSnapshot(snapshot_id="S-1", captured_at="2026-01-01")
        assert snap.overall_health == "green"
        assert snap.domain_views == []


# ── InMemoryAdapter Tests ────────────────────────────────────────


class TestInMemoryAdapter:
    def test_store_and_get_domain_view(self):
        adapter = InMemoryRadarAdapter()
        view = DomainDriftView(domain="intelops", total_signals=5)
        adapter.store_domain_view(view)
        views = adapter.get_domain_views()
        assert len(views) == 1
        assert views[0].total_signals == 5

    def test_domain_view_replaces_same_domain(self):
        adapter = InMemoryRadarAdapter()
        adapter.store_domain_view(DomainDriftView(domain="intelops", total_signals=3))
        adapter.store_domain_view(DomainDriftView(domain="intelops", total_signals=7))
        views = adapter.get_domain_views()
        assert len(views) == 1
        assert views[0].total_signals == 7

    def test_raw_signals(self):
        adapter = InMemoryRadarAdapter()
        adapter.store_raw_signals("intelops", [{"driftType": "time"}])
        adapter.store_raw_signals("intelops", [{"driftType": "bypass"}])
        signals = adapter.get_raw_signals("intelops")
        assert len(signals) == 2

    def test_correlations(self):
        adapter = InMemoryRadarAdapter()
        corr = DriftCorrelation(
            correlation_id="DC-1", domain_a="intelops", domain_b="franops",
            drift_type_a="time", drift_type_b="time", correlation_strength=0.8,
        )
        adapter.store_correlations([corr])
        assert len(adapter.get_correlations()) == 1

    def test_snapshots(self):
        adapter = InMemoryRadarAdapter()
        snap = RadarSnapshot(snapshot_id="S-1", captured_at="2026-01-01")
        adapter.store_snapshot(snap)
        assert len(adapter.get_snapshots()) == 1


# ── Correlation Tests ────────────────────────────────────────────


class TestCorrelation:
    def test_find_correlations_shared_type(self):
        views = [
            DomainDriftView(
                domain="intelops", total_signals=5,
                by_type={"time": 3, "bypass": 2},
                by_severity={"yellow": 5},
            ),
            DomainDriftView(
                domain="franops", total_signals=4,
                by_type={"time": 2, "freshness": 2},
                by_severity={"yellow": 4},
            ),
        ]
        correlations = find_correlations(views)
        assert len(correlations) == 1
        assert correlations[0].drift_type_a == "time"
        assert correlations[0].correlation_strength > 0

    def test_find_correlations_no_shared(self):
        views = [
            DomainDriftView(domain="a", by_type={"time": 1}),
            DomainDriftView(domain="b", by_type={"bypass": 1}),
        ]
        correlations = find_correlations(views)
        assert len(correlations) == 0

    def test_amplify_severity_green_to_yellow(self):
        corr = DriftCorrelation(
            correlation_id="DC-1", domain_a="a", domain_b="b",
            drift_type_a="t", drift_type_b="t", correlation_strength=0.7,
        )
        result = amplify_severity_score("green", [corr], threshold=0.5)
        assert result == "yellow"

    def test_amplify_severity_red_stays_red(self):
        corr = DriftCorrelation(
            correlation_id="DC-1", domain_a="a", domain_b="b",
            drift_type_a="t", drift_type_b="t", correlation_strength=0.9,
        )
        result = amplify_severity_score("red", [corr])
        assert result == "red"

    def test_amplify_severity_below_threshold(self):
        corr = DriftCorrelation(
            correlation_id="DC-1", domain_a="a", domain_b="b",
            drift_type_a="t", drift_type_b="t", correlation_strength=0.3,
        )
        result = amplify_severity_score("green", [corr], threshold=0.5)
        assert result == "green"


# ── Trending Tests ───────────────────────────────────────────────


class TestTrending:
    def test_compute_trends_basic(self):
        views = [
            DomainDriftView(
                domain="intelops",
                by_type={"time": 30},
                by_severity={"red": 5, "yellow": 10, "green": 15},
            ),
        ]
        trends = compute_trends(views, window_hours=24)
        assert len(trends) == 1
        assert trends[0].rate_of_change > 0
        assert trends[0].direction == "increasing"

    def test_compute_trends_low_rate(self):
        views = [
            DomainDriftView(
                domain="intelops",
                by_type={"time": 1},
                by_severity={"green": 1},
            ),
        ]
        trends = compute_trends(views, window_hours=24)
        assert trends[0].direction == "decreasing"


# ── Forecasting Tests ────────────────────────────────────────────


class TestForecasting:
    def test_project_drift_escalating(self):
        trends = [
            DriftTrend(
                fingerprint_key="intelops:time",
                domain="intelops",
                rate_of_change=2.0,
                direction="increasing",
                severity_trajectory="escalating",
            ),
        ]
        forecasts = project_drift(trends, horizon_hours=12)
        assert len(forecasts) == 1
        assert forecasts[0].projected_severity in ("yellow", "red")

    def test_project_drift_zero_rate(self):
        trends = [
            DriftTrend(
                fingerprint_key="x:y",
                domain="x",
                rate_of_change=0.0,
            ),
        ]
        forecasts = project_drift(trends)
        assert forecasts[0].projected_severity == "green"


# ── Prioritization Tests ────────────────────────────────────────


class TestPrioritization:
    def test_rank_remediations_sorted(self):
        trends = [
            DriftTrend(fingerprint_key="a:t", domain="a",
                       rate_of_change=5.0, severity_trajectory="escalating"),
            DriftTrend(fingerprint_key="b:t", domain="b",
                       rate_of_change=0.5, severity_trajectory="stable"),
        ]
        forecasts = project_drift(trends)
        priorities = rank_remediations(trends, forecasts)
        assert len(priorities) == 2
        assert priorities[0].priority_score >= priorities[1].priority_score
        assert priorities[0].recommended_action in ("immediate_investigation", "scheduled_review")


# ── DriftRadar Runtime Tests ────────────────────────────────────


class TestDriftRadar:
    def test_ingest_and_snapshot(self):
        radar = DriftRadar(InMemoryRadarAdapter())
        radar.ingest_domain_signals("intelops", [
            {"driftType": "time", "severity": "yellow"},
            {"driftType": "time", "severity": "red"},
            {"driftType": "bypass", "severity": "green"},
        ])
        radar.ingest_domain_signals("franops", [
            {"driftType": "time", "severity": "yellow"},
        ])
        snap = radar.snapshot()
        assert snap.overall_health in ("yellow", "red")
        assert len(snap.domain_views) == 2
        assert len(snap.trends) > 0

    def test_correlate(self):
        radar = DriftRadar(InMemoryRadarAdapter())
        radar.ingest_domain_signals("a", [{"driftType": "time", "severity": "yellow"}])
        radar.ingest_domain_signals("b", [{"driftType": "time", "severity": "yellow"}])
        correlations = radar.correlate()
        assert len(correlations) >= 1

    def test_amplify_severity(self):
        radar = DriftRadar(InMemoryRadarAdapter())
        radar.ingest_domain_signals("a", [{"driftType": "time", "severity": "yellow"}])
        radar.ingest_domain_signals("b", [{"driftType": "time", "severity": "yellow"}])
        radar.correlate()
        result = radar.amplify_severity("green")
        assert result in ("green", "yellow", "red")

    def test_prioritize(self):
        radar = DriftRadar(InMemoryRadarAdapter())
        radar.ingest_domain_signals("ops", [
            {"driftType": "time", "severity": "red"},
            {"driftType": "time", "severity": "red"},
        ])
        priorities = radar.prioritize()
        assert len(priorities) >= 1

    def test_adapter_name(self):
        radar = DriftRadar(InMemoryRadarAdapter())
        assert radar.adapter_name == "inmemory"
