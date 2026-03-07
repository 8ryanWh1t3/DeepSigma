"""Tests for core.severity — centralized severity scoring."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.severity import (  # noqa: E402
    DRIFT_TYPE_WEIGHTS,
    SEVERITY_ORDER,
    aggregate_severity,
    classify_severity,
    compute_severity_score,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_severity_order_has_three_levels(self):
        assert set(SEVERITY_ORDER.keys()) == {"red", "yellow", "green"}

    def test_severity_order_red_highest(self):
        assert SEVERITY_ORDER["red"] > SEVERITY_ORDER["yellow"] > SEVERITY_ORDER["green"]

    def test_drift_type_weights_bounded(self):
        for dt, w in DRIFT_TYPE_WEIGHTS.items():
            assert 0.0 <= w <= 1.0, f"{dt} weight {w} out of bounds"


class TestComputeSeverityScore:
    """Tests for compute_severity_score()."""

    def test_known_type_red(self):
        score = compute_severity_score("authority_mismatch", "red")
        assert score == pytest.approx(0.9, abs=0.001)

    def test_known_type_yellow(self):
        score = compute_severity_score("authority_mismatch", "yellow")
        assert score == pytest.approx(0.9 * 0.6, abs=0.001)

    def test_known_type_green(self):
        score = compute_severity_score("authority_mismatch", "green")
        assert score == pytest.approx(0.9 * 0.2, abs=0.001)

    def test_unknown_type_uses_default(self):
        score = compute_severity_score("unknown_type", "red")
        assert score == pytest.approx(0.5 * 1.0, abs=0.001)

    def test_unknown_severity_uses_default(self):
        score = compute_severity_score("time", "critical")
        assert score == pytest.approx(0.3 * 0.5, abs=0.001)

    def test_recurrence_boost(self):
        base = compute_severity_score("freshness", "yellow")
        boosted = compute_severity_score("freshness", "yellow", {"recurrence_count": 2})
        assert boosted > base
        assert boosted == pytest.approx(base + 0.10, abs=0.001)

    def test_recurrence_zero_no_boost(self):
        base = compute_severity_score("freshness", "yellow")
        same = compute_severity_score("freshness", "yellow", {"recurrence_count": 0})
        assert same == base

    def test_capped_at_one(self):
        score = compute_severity_score("authority_mismatch", "red", {"recurrence_count": 100})
        assert score == 1.0

    def test_score_non_negative(self):
        score = compute_severity_score("time", "green")
        assert score >= 0.0

    def test_returns_float_three_decimals(self):
        score = compute_severity_score("freshness", "yellow")
        assert isinstance(score, float)
        # At most 3 decimal places
        assert score == round(score, 3)


class TestClassifySeverity:
    """Tests for classify_severity()."""

    def test_red_threshold(self):
        assert classify_severity(0.7) == "red"
        assert classify_severity(0.9) == "red"
        assert classify_severity(1.0) == "red"

    def test_yellow_threshold(self):
        assert classify_severity(0.3) == "yellow"
        assert classify_severity(0.5) == "yellow"
        assert classify_severity(0.69) == "yellow"

    def test_green_threshold(self):
        assert classify_severity(0.0) == "green"
        assert classify_severity(0.1) == "green"
        assert classify_severity(0.29) == "green"


class TestAggregateSeverity:
    """Tests for aggregate_severity()."""

    def test_empty_signals(self):
        result = aggregate_severity([])
        assert result["overall"] == "green"
        assert result["maxScore"] == 0.0
        assert result["signalCount"] == 0
        assert result["breakdown"] == {}

    def test_single_signal(self):
        signals = [{"driftType": "authority_mismatch", "severity": "red"}]
        result = aggregate_severity(signals)
        assert result["overall"] == "red"
        assert result["signalCount"] == 1
        assert result["breakdown"]["authority_mismatch"] == 1

    def test_multiple_signals_max_wins(self):
        signals = [
            {"driftType": "time", "severity": "green"},
            {"driftType": "authority_mismatch", "severity": "red"},
        ]
        result = aggregate_severity(signals)
        assert result["overall"] == "red"
        assert result["maxScore"] == pytest.approx(0.9, abs=0.001)

    def test_breakdown_counts(self):
        signals = [
            {"driftType": "freshness", "severity": "yellow"},
            {"driftType": "freshness", "severity": "red"},
            {"driftType": "time", "severity": "green"},
        ]
        result = aggregate_severity(signals)
        assert result["breakdown"]["freshness"] == 2
        assert result["breakdown"]["time"] == 1
        assert result["signalCount"] == 3
