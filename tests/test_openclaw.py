"""
Tests for OpenClaw adapter — contract verification supervisor.
"""
import pytest

from adapters.openclaw.adapter import OpenClawSupervisor


POLICY_PACK = {
    "contracts": {
        "deploy": {
            "contractId": "deploy-v1",
            "preconditions": [
                {"field": "env_ready", "equals": True, "message": "Environment must be ready"},
                {"field": "tests_pass", "equals": True},
            ],
            "postconditions": [
                {"field": "status", "equals": "deployed"},
            ],
        },
        "scale": {
            "contractId": "scale-v1",
            "preconditions": [],
            "postconditions": [],
        },
    }
}


@pytest.fixture
def supervisor():
    return OpenClawSupervisor(POLICY_PACK)


# ── Contract retrieval ──


class TestGetContract:
    def test_known(self, supervisor):
        c = supervisor.get_contract("deploy")
        assert c["contractId"] == "deploy-v1"

    def test_unknown(self, supervisor):
        assert supervisor.get_contract("unknown") == {}


# ── Precondition checks ──


class TestPreconditions:
    def test_pass(self, supervisor):
        ctx = {"env_ready": True, "tests_pass": True}
        result = supervisor.check_preconditions("deploy", ctx)
        assert result.passed
        assert result.violations == []

    def test_fail(self, supervisor):
        ctx = {"env_ready": False, "tests_pass": True}
        result = supervisor.check_preconditions("deploy", ctx)
        assert not result.passed
        assert len(result.violations) == 1
        assert result.violations[0].field == "env_ready"
        assert result.violations[0].condition_type == "precondition"

    def test_fail_multiple(self, supervisor):
        ctx = {"env_ready": False, "tests_pass": False}
        result = supervisor.check_preconditions("deploy", ctx)
        assert not result.passed
        assert len(result.violations) == 2

    def test_no_contract(self, supervisor):
        result = supervisor.check_preconditions("unknown", {})
        assert result.passed

    def test_empty_preconditions(self, supervisor):
        result = supervisor.check_preconditions("scale", {})
        assert result.passed


# ── Postcondition checks ──


class TestPostconditions:
    def test_pass(self, supervisor):
        result = supervisor.check_postconditions("deploy", {}, {"status": "deployed"})
        assert result.passed

    def test_fail(self, supervisor):
        result = supervisor.check_postconditions("deploy", {}, {"status": "failed"})
        assert not result.passed
        assert result.violations[0].field == "status"
        assert result.violations[0].condition_type == "postcondition"

    def test_no_contract(self, supervisor):
        result = supervisor.check_postconditions("unknown", {}, {})
        assert result.passed


# ── Supervise lifecycle ──


class TestSupervise:
    def test_success(self, supervisor):
        ctx = {"env_ready": True, "tests_pass": True}
        result = supervisor.supervise("deploy", ctx, lambda c: {"status": "deployed"})
        assert result["outcome"] == "success"
        assert result["result"] == {"status": "deployed"}
        assert "elapsed_ms" in result

    def test_blocked_by_precondition(self, supervisor):
        ctx = {"env_ready": False, "tests_pass": True}
        result = supervisor.supervise("deploy", ctx, lambda c: {"status": "deployed"})
        assert result["outcome"] == "blocked"
        assert result["reason"] == "precondition_failed"
        assert len(result["violations"]) == 1

    def test_postcondition_failed(self, supervisor):
        ctx = {"env_ready": True, "tests_pass": True}
        result = supervisor.supervise("deploy", ctx, lambda c: {"status": "error"})
        assert result["outcome"] == "postcondition_failed"
        assert len(result["violations"]) == 1

    def test_action_exception(self, supervisor):
        ctx = {"env_ready": True, "tests_pass": True}
        def boom(c):
            raise ValueError("deploy crashed")
        result = supervisor.supervise("deploy", ctx, boom)
        assert result["outcome"] == "error"
        assert "deploy crashed" in result["reason"]

    def test_no_contracts(self, supervisor):
        result = supervisor.supervise("scale", {}, lambda c: {"scaled": True})
        assert result["outcome"] == "success"


# ── Violations log ──


class TestViolationsLog:
    def test_accumulates(self, supervisor):
        ctx = {"env_ready": False, "tests_pass": False}
        supervisor.check_preconditions("deploy", ctx)
        supervisor.check_preconditions("deploy", ctx)
        assert len(supervisor.violations) == 4

    def test_returns_copy(self, supervisor):
        ctx = {"env_ready": False, "tests_pass": True}
        supervisor.check_preconditions("deploy", ctx)
        v1 = supervisor.violations
        v1.clear()
        assert len(supervisor.violations) == 1  # original untouched
