"""Tests for GovernanceCallbackHandler."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from langchain_deepsigma.governance import GovernanceCallbackHandler, DTEViolationError


class TestGovernanceCallbackHandler:

    def test_init_defaults(self, mock_enforcer_clean):
        h = GovernanceCallbackHandler(dte_enforcer=mock_enforcer_clean)
        assert h.name == "governance_callback"
        assert h.should_degrade is False
        assert h.violations == []

    def test_on_chain_start_sets_timer(self, mock_enforcer_clean, run_id):
        h = GovernanceCallbackHandler(dte_enforcer=mock_enforcer_clean)
        assert h._start_time is None
        h.on_chain_start({}, {}, run_id=run_id)
        assert h._start_time is not None
        assert h._chain_depth == 1

    def test_clean_enforcer_no_violations(self, mock_enforcer_clean, run_id):
        h = GovernanceCallbackHandler(dte_enforcer=mock_enforcer_clean)
        h.on_chain_start({}, {}, run_id=run_id)
        h.on_llm_end(MagicMock(), run_id=run_id)
        assert h.violations == []

    def test_violating_enforcer_raises(self, mock_enforcer_violating, run_id):
        h = GovernanceCallbackHandler(
            dte_enforcer=mock_enforcer_violating,
            on_violation="raise",
        )
        h.on_chain_start({}, {}, run_id=run_id)
        with pytest.raises(DTEViolationError) as exc_info:
            h.on_llm_end(MagicMock(), run_id=run_id)
        assert len(exc_info.value.violations) == 1

    def test_violating_enforcer_degrade_mode(self, mock_enforcer_violating, run_id):
        h = GovernanceCallbackHandler(
            dte_enforcer=mock_enforcer_violating,
            on_violation="degrade",
        )
        h.on_chain_start({}, {}, run_id=run_id)
        h.on_llm_end(MagicMock(), run_id=run_id)
        assert h.should_degrade is True
        assert len(h.violations) == 1

    def test_summary_returns_structure(self, mock_enforcer_clean, run_id):
        h = GovernanceCallbackHandler(dte_enforcer=mock_enforcer_clean)
        h.on_chain_start({}, {}, run_id=run_id)
        h.on_tool_start({}, "input", run_id=run_id)
        s = h.summary()
        assert "elapsed_ms" in s
        assert s["tool_calls"] == 1
        assert s["chain_depth"] == 1
