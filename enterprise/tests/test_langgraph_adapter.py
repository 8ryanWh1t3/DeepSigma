"""Tests for LangGraph exhaust adapter."""
import asyncio

from adapters.langgraph_exhaust import LangGraphExhaustTracker


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_event(event_type: str, name: str = "test", run_id: str = "run-1", **kwargs):
    return {"event": event_type, "name": name, "run_id": run_id, "data": {}, **kwargs}


# -- Event handling --------------------------------------------------------


class TestGraphStart:
    def test_first_chain_start_is_graph_start(self):
        tracker = LangGraphExhaustTracker()
        result = _run(tracker.handle_event(_make_event("on_chain_start")))
        assert result is None
        assert len(tracker._buffer) == 1
        assert tracker._buffer[0]["event_type"] == "graph_start"

    def test_second_chain_start_is_node_start(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        _run(tracker.handle_event(_make_event("on_chain_start", name="node_a")))
        assert tracker._buffer[1]["event_type"] == "node_start"


class TestNodeEvents:
    def test_node_end_increments_count(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        _run(tracker.handle_event(_make_event("on_chain_end")))
        assert tracker._node_count == 1

    def test_multiple_node_ends(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        for _ in range(5):
            _run(tracker.handle_event(_make_event("on_chain_end")))
        assert tracker._node_count == 5


class TestToolEvents:
    def test_tool_start_and_end(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        _run(tracker.handle_event(_make_event("on_tool_start", name="search")))
        _run(tracker.handle_event(_make_event("on_tool_end", name="search")))
        assert tracker._tool_call_count == 1
        types = [e["event_type"] for e in tracker._buffer]
        assert "tool_start" in types
        assert "tool_end" in types

    def test_multiple_tool_calls(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        for _ in range(3):
            _run(tracker.handle_event(_make_event("on_tool_start")))
            _run(tracker.handle_event(_make_event("on_tool_end")))
        assert tracker._tool_call_count == 3


class TestUnknownEvents:
    def test_unknown_event_ignored(self):
        tracker = LangGraphExhaustTracker()
        result = _run(tracker.handle_event({"event": "on_something_weird", "name": "x", "run_id": "r"}))
        assert result is None
        assert len(tracker._buffer) == 0

    def test_empty_event_ignored(self):
        tracker = LangGraphExhaustTracker()
        result = _run(tracker.handle_event({}))
        assert result is None
        assert len(tracker._buffer) == 0


# -- DTE integration -------------------------------------------------------


class TestDTEViolations:
    def test_violations_on_tool_end(self):
        from engine.dte_enforcer import DTEEnforcer

        dte = DTEEnforcer({"deadlineMs": 0, "limits": {"maxToolCalls": 0}})
        tracker = LangGraphExhaustTracker(dte_enforcer=dte)
        _run(tracker.handle_event(_make_event("on_chain_start")))
        violations = _run(tracker.handle_event(_make_event("on_tool_end")))
        assert violations is not None
        assert len(violations) >= 1
        v = violations[0]
        assert "gate" in v
        assert "severity" in v
        assert "message" in v

    def test_violations_on_node_end(self):
        from engine.dte_enforcer import DTEEnforcer

        dte = DTEEnforcer({"deadlineMs": 0, "limits": {"maxHops": 0}})
        tracker = LangGraphExhaustTracker(dte_enforcer=dte)
        _run(tracker.handle_event(_make_event("on_chain_start")))
        violations = _run(tracker.handle_event(_make_event("on_chain_end")))
        assert violations is not None
        assert any(v["gate"] == "limits" for v in violations)

    def test_violations_accumulated_in_summary(self):
        from engine.dte_enforcer import DTEEnforcer

        dte = DTEEnforcer({"deadlineMs": 0, "limits": {"maxToolCalls": 0}})
        tracker = LangGraphExhaustTracker(dte_enforcer=dte)
        _run(tracker.handle_event(_make_event("on_chain_start")))
        _run(tracker.handle_event(_make_event("on_tool_end")))
        s = tracker.summary()
        assert len(s["violations"]) >= 1


class TestNoDTE:
    def test_no_dte_graceful(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        result = _run(tracker.handle_event(_make_event("on_chain_end")))
        assert result is None

    def test_no_dte_tool_end_graceful(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        result = _run(tracker.handle_event(_make_event("on_tool_end")))
        assert result is None


# -- Summary ---------------------------------------------------------------


class TestSummary:
    def test_summary_structure(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        _run(tracker.handle_event(_make_event("on_chain_end")))
        _run(tracker.handle_event(_make_event("on_tool_start")))
        _run(tracker.handle_event(_make_event("on_tool_end")))
        s = tracker.summary()
        assert s["node_count"] == 1
        assert s["tool_call_count"] == 1
        assert "elapsed_ms" in s
        assert isinstance(s["elapsed_ms"], float)
        assert isinstance(s["violations"], list)

    def test_empty_summary(self):
        tracker = LangGraphExhaustTracker()
        s = tracker.summary()
        assert s["node_count"] == 0
        assert s["tool_call_count"] == 0
        assert s["elapsed_ms"] == 0.0
        assert s["violations"] == []


# -- Flush -----------------------------------------------------------------


class TestFlush:
    def test_flush_clears_buffer(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.handle_event(_make_event("on_chain_start")))
        assert len(tracker._buffer) > 0
        _run(tracker.flush())
        assert len(tracker._buffer) == 0

    def test_flush_empty_noop(self):
        tracker = LangGraphExhaustTracker()
        _run(tracker.flush())  # should not raise
        assert len(tracker._buffer) == 0


# -- Event record structure ------------------------------------------------


class TestEventRecord:
    def test_record_fields(self):
        tracker = LangGraphExhaustTracker(project="test-proj")
        _run(tracker.handle_event(_make_event("on_chain_start", name="my_graph", run_id="r-123")))
        rec = tracker._buffer[0]
        assert rec["event_type"] == "graph_start"
        assert rec["name"] == "my_graph"
        assert rec["run_id"] == "r-123"
        assert rec["project"] == "test-proj"
        assert "event_id" in rec
        assert "timestamp" in rec
