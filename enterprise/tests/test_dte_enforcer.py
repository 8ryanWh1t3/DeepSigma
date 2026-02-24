"""Tests for DTE Enforcer — active constraint validation."""
from engine.dte_enforcer import DTEEnforcer, DTEViolation


SAMPLE_DTE = {
    "decisionType": "deploy",
    "version": "1.0",
    "deadlineMs": 120,
    "stageBudgetsMs": {
        "context": 40,
        "plan": 30,
        "act": 30,
        "verify": 20,
    },
    "freshness": {
        "defaultTtlMs": 300,
        "featureTtls": {
            "price_feed": 100,
            "user_profile": 500,
        },
        "allowStaleIfSafe": False,
    },
    "limits": {
        "maxHops": 5,
        "maxFanout": 3,
        "maxToolCalls": 20,
        "maxChainDepth": 4,
    },
}


class TestWithinEnvelope:
    def test_all_within_returns_empty(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            stage_elapsed={"context": 30, "plan": 20, "act": 20, "verify": 10},
            feature_ages={"price_feed": 50, "user_profile": 200},
            counts={"hops": 2, "tool_calls": 10},
        )
        assert violations == []

    def test_no_optional_args(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(elapsed_ms=80)
        assert violations == []


class TestDeadline:
    def test_deadline_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(elapsed_ms=150)
        assert len(violations) == 1
        v = violations[0]
        assert v.gate == "deadline"
        assert v.severity == "hard"
        assert v.limit_value == 120
        assert v.actual_value == 150

    def test_deadline_exact_is_ok(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(elapsed_ms=120)
        assert violations == []

    def test_no_deadline_in_spec(self):
        enforcer = DTEEnforcer({"freshness": {"defaultTtlMs": 300}})
        violations = enforcer.enforce(elapsed_ms=99999)
        assert violations == []


class TestStageBudgets:
    def test_single_stage_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            stage_elapsed={"context": 50, "plan": 20, "act": 5, "verify": 5},
        )
        assert len(violations) == 1
        assert violations[0].gate == "stage_budget"
        assert violations[0].field == "stageBudgetsMs.context"
        assert violations[0].severity == "soft"

    def test_multiple_stages_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            stage_elapsed={"context": 50, "plan": 40, "act": 35, "verify": 25},
        )
        assert len(violations) == 4
        gates = {v.field for v in violations}
        assert "stageBudgetsMs.context" in gates
        assert "stageBudgetsMs.plan" in gates
        assert "stageBudgetsMs.act" in gates
        assert "stageBudgetsMs.verify" in gates

    def test_partial_stage_elapsed(self):
        """Only stages provided are checked."""
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            stage_elapsed={"context": 50},  # only context provided, exceeds 40
        )
        assert len(violations) == 1
        assert violations[0].field == "stageBudgetsMs.context"


class TestFreshness:
    def test_feature_ttl_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            feature_ages={"price_feed": 200},  # exceeds 100ms TTL
        )
        assert len(violations) == 1
        assert violations[0].gate == "feature_ttl"
        assert violations[0].severity == "hard"
        assert violations[0].field == "featureTtls.price_feed"

    def test_default_ttl_used(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            feature_ages={"unknown_feature": 400},  # exceeds default 300ms
        )
        assert len(violations) == 1
        assert violations[0].gate == "feature_ttl"
        assert violations[0].limit_value == 300  # defaultTtlMs

    def test_feature_within_ttl(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            feature_ages={"price_feed": 50, "user_profile": 200},
        )
        assert violations == []

    def test_allow_stale_if_safe(self):
        """allowStaleIfSafe=True downgrades TTL violations to 'soft'."""
        spec = {**SAMPLE_DTE, "freshness": {
            "defaultTtlMs": 100,
            "allowStaleIfSafe": True,
        }}
        enforcer = DTEEnforcer(spec)
        violations = enforcer.enforce(
            elapsed_ms=80,
            feature_ages={"some_feature": 200},
        )
        assert len(violations) == 1
        assert violations[0].severity == "soft"

    def test_no_freshness_in_spec(self):
        enforcer = DTEEnforcer({"deadlineMs": 1000})
        violations = enforcer.enforce(
            elapsed_ms=80,
            feature_ages={"any": 99999},
        )
        assert violations == []


class TestLimits:
    def test_hops_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            counts={"hops": 10},
        )
        assert len(violations) == 1
        assert violations[0].gate == "limits"
        assert violations[0].field == "limits.maxHops"
        assert violations[0].severity == "hard"

    def test_tool_calls_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            counts={"tool_calls": 25},
        )
        assert len(violations) == 1
        assert violations[0].field == "limits.maxToolCalls"

    def test_multiple_limits_exceeded(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            counts={"hops": 10, "fanout": 5, "tool_calls": 25, "chain_depth": 6},
        )
        assert len(violations) == 4

    def test_limits_within(self):
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=80,
            counts={"hops": 3, "tool_calls": 15, "chain_depth": 2},
        )
        assert violations == []


class TestCombined:
    def test_multiple_gate_violations(self):
        """Deadline + stage budget + TTL + limits all violated at once."""
        enforcer = DTEEnforcer(SAMPLE_DTE)
        violations = enforcer.enforce(
            elapsed_ms=200,
            stage_elapsed={"context": 50, "plan": 20, "act": 20, "verify": 10},
            feature_ages={"price_feed": 200},
            counts={"hops": 10},
        )
        gates = {v.gate for v in violations}
        assert "deadline" in gates
        assert "stage_budget" in gates
        assert "feature_ttl" in gates
        assert "limits" in gates

    def test_violation_dataclass_fields(self):
        v = DTEViolation(
            gate="deadline",
            field="deadlineMs",
            limit_value=120,
            actual_value=200,
            severity="hard",
            message="test",
        )
        assert v.gate == "deadline"
        assert v.field == "deadlineMs"
        assert v.limit_value == 120
        assert v.actual_value == 200
        assert v.severity == "hard"
        assert v.message == "test"
