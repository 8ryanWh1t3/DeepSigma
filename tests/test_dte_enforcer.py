"""Tests for core.dte_enforcer — Decision Timing Envelope constraint validation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.dte_enforcer import DTEEnforcer, DTEViolation  # noqa: E402


def _make_spec(**overrides):
    """Build a minimal DTE spec dict."""
    spec = {
        "deadlineMs": 100,
        "stageBudgetsMs": {
            "context": 30,
            "plan": 30,
            "act": 30,
            "verify": 30,
        },
        "freshness": {
            "defaultTtlMs": 500,
            "featureTtls": {"price_feed": 300},
            "allowStaleIfSafe": False,
        },
        "limits": {
            "maxHops": 5,
            "maxFanout": 10,
            "maxToolCalls": 20,
            "maxChainDepth": 3,
        },
    }
    spec.update(overrides)
    return spec


class TestDTEViolation:
    def test_fields(self):
        v = DTEViolation(
            gate="deadline",
            field="deadlineMs",
            limit_value=100,
            actual_value=150,
            severity="hard",
            message="exceeded",
        )
        assert v.gate == "deadline"
        assert v.severity == "hard"


class TestDeadline:
    def test_within_deadline(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(elapsed_ms=50)
        assert len(violations) == 0

    def test_at_deadline(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(elapsed_ms=100)
        assert len(violations) == 0

    def test_exceeds_deadline(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(elapsed_ms=150)
        assert len(violations) == 1
        assert violations[0].gate == "deadline"
        assert violations[0].severity == "hard"
        assert violations[0].actual_value == 150

    def test_no_deadline_spec(self):
        enforcer = DTEEnforcer({"limits": {}})
        violations = enforcer.enforce(elapsed_ms=9999)
        assert len(violations) == 0


class TestStageBudgets:
    def test_all_within_budget(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            stage_elapsed={"context": 10, "plan": 10, "act": 10, "verify": 10},
        )
        assert len(violations) == 0

    def test_one_stage_exceeded(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            stage_elapsed={"context": 50, "plan": 10, "act": 10, "verify": 10},
        )
        stage_violations = [v for v in violations if v.gate == "stage_budget"]
        assert len(stage_violations) == 1
        assert "context" in stage_violations[0].field
        assert stage_violations[0].severity == "soft"

    def test_multiple_stages_exceeded(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            stage_elapsed={"context": 50, "plan": 50, "act": 10, "verify": 10},
        )
        stage_violations = [v for v in violations if v.gate == "stage_budget"]
        assert len(stage_violations) == 2

    def test_no_stage_budgets_spec(self):
        enforcer = DTEEnforcer({"deadlineMs": 100})
        violations = enforcer.enforce(
            elapsed_ms=50,
            stage_elapsed={"context": 999},
        )
        stage_violations = [v for v in violations if v.gate == "stage_budget"]
        assert len(stage_violations) == 0


class TestFreshness:
    def test_within_ttl(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            feature_ages={"price_feed": 100},
        )
        ttl_violations = [v for v in violations if v.gate == "feature_ttl"]
        assert len(ttl_violations) == 0

    def test_exceeds_feature_ttl(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            feature_ages={"price_feed": 400},
        )
        ttl_violations = [v for v in violations if v.gate == "feature_ttl"]
        assert len(ttl_violations) == 1
        assert ttl_violations[0].severity == "hard"

    def test_default_ttl_applied(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            feature_ages={"unknown_feature": 600},
        )
        ttl_violations = [v for v in violations if v.gate == "feature_ttl"]
        assert len(ttl_violations) == 1

    def test_allow_stale_if_safe(self):
        spec = _make_spec()
        spec["freshness"]["allowStaleIfSafe"] = True
        enforcer = DTEEnforcer(spec)
        violations = enforcer.enforce(
            elapsed_ms=50,
            feature_ages={"price_feed": 400},
        )
        ttl_violations = [v for v in violations if v.gate == "feature_ttl"]
        assert len(ttl_violations) == 1
        assert ttl_violations[0].severity == "soft"

    def test_no_freshness_spec(self):
        enforcer = DTEEnforcer({"deadlineMs": 100})
        violations = enforcer.enforce(
            elapsed_ms=50,
            feature_ages={"price_feed": 9999},
        )
        ttl_violations = [v for v in violations if v.gate == "feature_ttl"]
        assert len(ttl_violations) == 0


class TestLimits:
    def test_within_limits(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            counts={"hops": 3, "tool_calls": 10},
        )
        limit_violations = [v for v in violations if v.gate == "limits"]
        assert len(limit_violations) == 0

    def test_exceeds_hops(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            counts={"hops": 10},
        )
        limit_violations = [v for v in violations if v.gate == "limits"]
        assert len(limit_violations) == 1
        assert limit_violations[0].severity == "hard"

    def test_exceeds_tool_calls(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            counts={"tool_calls": 25},
        )
        limit_violations = [v for v in violations if v.gate == "limits"]
        assert len(limit_violations) == 1

    def test_multiple_limit_violations(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            counts={"hops": 10, "tool_calls": 25, "chain_depth": 5},
        )
        limit_violations = [v for v in violations if v.gate == "limits"]
        assert len(limit_violations) == 3


class TestCamelCaseInput:
    def test_camel_case_normalised(self):
        spec = {"deadlineMs": 100}
        enforcer = DTEEnforcer(spec)
        violations = enforcer.enforce(elapsed_ms=150)
        assert len(violations) == 1


class TestCombined:
    def test_multiple_gates_violated(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=150,
            stage_elapsed={"context": 50},
            feature_ages={"price_feed": 400},
            counts={"hops": 10},
        )
        gates = {v.gate for v in violations}
        assert "deadline" in gates
        assert "stage_budget" in gates
        assert "feature_ttl" in gates
        assert "limits" in gates

    def test_clean_run_no_violations(self):
        enforcer = DTEEnforcer(_make_spec())
        violations = enforcer.enforce(
            elapsed_ms=50,
            stage_elapsed={"context": 10, "plan": 10, "act": 10, "verify": 10},
            feature_ages={"price_feed": 100},
            counts={"hops": 2, "tool_calls": 5},
        )
        assert len(violations) == 0
