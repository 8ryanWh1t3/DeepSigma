"""Tests for adapters.langchain_governance — DTE-enforcing callback handler."""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.dte_enforcer import DTEEnforcer
from adapters.langchain_governance import GovernanceCallbackHandler, DTEViolationError


def _make_dte(deadline_ms=100, max_tool_calls=5, max_chain_depth=3):
    return DTEEnforcer({
        "deadlineMs": deadline_ms,
        "limits": {
            "maxToolCalls": max_tool_calls,
            "maxChainDepth": max_chain_depth,
        },
    })


class TestGovernanceCallbackHandler:
    def test_no_violation_within_envelope(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=999999))
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        handler.on_llm_end(None, run_id=run_id)
        handler.on_chain_end({}, run_id=run_id)
        assert len(handler.violations) == 0

    def test_deadline_violation_raise(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0))
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        with pytest.raises(DTEViolationError) as exc_info:
            handler.on_llm_end(None, run_id=run_id)
        assert len(exc_info.value.violations) > 0
        assert "deadline" in exc_info.value.violations[0]["gate"].lower() or "Deadline" in exc_info.value.violations[0]["message"]

    def test_tool_call_limit_violation(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=999999, max_tool_calls=2))
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_tool_start({}, "input1", run_id=run_id)
        handler.on_tool_end("out1", run_id=run_id)
        handler.on_tool_start({}, "input2", run_id=run_id)
        handler.on_tool_end("out2", run_id=run_id)
        handler.on_tool_start({}, "input3", run_id=run_id)
        with pytest.raises(DTEViolationError):
            handler.on_tool_end("out3", run_id=run_id)

    def test_on_violation_log(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0), on_violation="log")
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        # Should NOT raise
        handler.on_llm_end(None, run_id=run_id)
        assert len(handler.violations) > 0

    def test_on_violation_degrade(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0), on_violation="degrade")
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        handler.on_llm_end(None, run_id=run_id)
        assert handler.should_degrade is True

    def test_summary_structure(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=999999))
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_tool_start({}, "input", run_id=run_id)
        handler.on_tool_end("output", run_id=run_id)
        handler.on_chain_end({}, run_id=run_id)
        summary = handler.summary()
        assert "elapsed_ms" in summary
        assert summary["tool_calls"] == 1
        assert "violations" in summary

    def test_chain_depth_tracking(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=999999))
        run_id1 = uuid4()
        run_id2 = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id1)
        handler.on_chain_start({}, {}, run_id=run_id2)
        assert handler._chain_depth == 2
        handler.on_chain_end({}, run_id=run_id2)
        assert handler._chain_depth == 1
        handler.on_chain_end({}, run_id=run_id1)
        assert handler._chain_depth == 0

    def test_no_dte_graceful(self):
        handler = GovernanceCallbackHandler(dte_enforcer=None)
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        handler.on_llm_end(None, run_id=run_id)
        handler.on_chain_end({}, run_id=run_id)
        assert len(handler.violations) == 0

    def test_violation_error_message(self):
        error = DTEViolationError([
            {"gate": "deadline", "field": "deadlineMs", "limit": 100, "actual": 200, "severity": "hard", "message": "Deadline exceeded: 200ms > 100ms"},
        ])
        assert "200ms" in str(error)
        assert len(error.violations) == 1

    def test_violations_property_is_copy(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0), on_violation="log")
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        handler.on_llm_end(None, run_id=run_id)
        v1 = handler.violations
        v1.clear()
        assert len(handler.violations) > 0  # original not mutated

    def test_multiple_violations_accumulate(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0), on_violation="log")
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_start({}, ["test"], run_id=run_id)
        handler.on_llm_end(None, run_id=run_id)
        count1 = len(handler.violations)
        handler.on_tool_start({}, "in", run_id=run_id)
        handler.on_tool_end("out", run_id=run_id)
        assert len(handler.violations) >= count1

    def test_composability_with_exhaust(self):
        """Both handlers can be instantiated without conflict."""
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        exhaust = ExhaustCallbackHandler()
        governance = GovernanceCallbackHandler(dte_enforcer=_make_dte())
        # Both should have the name attribute
        assert exhaust.name == "exhaust_callback"
        assert governance.name == "governance_callback"

    def test_on_llm_error_does_not_raise(self):
        handler = GovernanceCallbackHandler(dte_enforcer=_make_dte(deadline_ms=0))
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_llm_error(RuntimeError("test"), run_id=run_id)
        # Should not raise or add violations
