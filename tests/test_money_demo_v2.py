"""Regression test for the v2 Money Demo pipeline (domain modes)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
_ENTERPRISE_SRC = _REPO_ROOT / "enterprise" / "src"
for p in (_SRC_ROOT, _ENTERPRISE_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from demos.money_demo.pipeline import MoneyDemoResult, load_fixtures, run_pipeline


class TestMoneyDemoFixtures:

    def test_fixtures_load(self):
        fixtures = load_fixtures()
        assert "baseline" in fixtures
        assert "delta" in fixtures
        assert len(fixtures["baseline"]["claims"]) == 3
        assert len(fixtures["delta"]["claims"]) == 1

    def test_baseline_claims_valid(self):
        fixtures = load_fixtures()
        for claim in fixtures["baseline"]["claims"]:
            assert "claimId" in claim
            assert "statement" in claim
            assert "confidence" in claim

    def test_delta_has_contradiction(self):
        fixtures = load_fixtures()
        delta = fixtures["delta"]["claims"][0]
        assert "contradicts" in delta.get("graph", {})


class TestMoneyDemoPipeline:

    def test_pipeline_completes(self):
        result = run_pipeline()
        assert len(result.steps) == 10

    def test_all_steps_ok(self):
        result = run_pipeline()
        for step in result.steps:
            assert step["status"] == "ok", f"Step {step['step']} failed"

    def test_baseline_claims_ingested(self):
        result = run_pipeline()
        assert result.baseline_claims == 3

    def test_delta_claims_ingested(self):
        result = run_pipeline()
        assert result.delta_claims == 1

    def test_drift_detected(self):
        result = run_pipeline()
        assert result.drift_signals_total > 0

    def test_retcon_executed(self):
        result = run_pipeline()
        assert result.retcon_executed

    def test_cascade_triggered(self):
        result = run_pipeline()
        assert result.cascade_rules_triggered > 0

    def test_episode_sealed(self):
        result = run_pipeline()
        assert result.episode_sealed

    def test_coherence_score_computed(self):
        result = run_pipeline()
        assert result.coherence_score > 0

    def test_audit_trail_exists(self):
        result = run_pipeline()
        assert result.audit_entries > 0

    def test_result_serializable(self):
        result = run_pipeline()
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "steps" in d
        assert len(d["steps"]) == 10
