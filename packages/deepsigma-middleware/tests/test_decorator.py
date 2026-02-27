"""Tests for the @log_decision decorator and configure()."""
from __future__ import annotations

import asyncio

import pytest

from deepsigma_middleware.decorator import configure, log_decision, get_session, reset_session


@pytest.fixture(autouse=True)
def clean_session():
    reset_session()
    yield
    reset_session()


class TestConfigure:

    def test_configure_sets_agent_id(self):
        configure(agent_id="test-api")
        session = get_session()
        assert session.agent_id == "test-api"

    def test_get_session_creates_on_demand(self):
        configure(agent_id="auto-create")
        session = get_session()
        assert session.agent_id == "auto-create"

    def test_get_session_returns_same_instance(self):
        configure(agent_id="stable")
        s1 = get_session()
        s2 = get_session()
        assert s1 is s2


class TestLogDecisionDecorator:

    def test_decorator_logs_decision(self):
        configure(agent_id="decorator-test")

        @log_decision(actor_type="api", decision_type="endpoint")
        def my_handler():
            return "ok"

        result = my_handler()
        assert result == "ok"
        session = get_session()
        assert len(session._episodes) >= 1

    def test_decorator_preserves_function_name(self):
        @log_decision()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_async_decorator_detected(self):
        """Verify async functions get the async wrapper."""
        @log_decision(actor_type="worker", decision_type="task")
        async def async_handler():
            return "async-ok"

        assert asyncio.iscoroutinefunction(async_handler)
        assert async_handler.__name__ == "async_handler"

    def test_decorator_uses_custom_decision_type(self):
        configure(agent_id="custom-type")

        @log_decision(decision_type="webhook")
        def webhook_handler():
            return 42

        webhook_handler()
        session = get_session()
        last_ep = session._episodes[-1]
        assert last_ep["decisionType"] == "webhook"
