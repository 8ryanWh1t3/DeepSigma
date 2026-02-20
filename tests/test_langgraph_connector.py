"""Tests for adapters/langgraph/connector.py — LangGraph trace connector.

Run:  pytest tests/test_langgraph_connector.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.langgraph.connector import LangGraphConnector
from connectors.contract import RecordEnvelope, validate_envelope

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "connectors" / "langgraph_small"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _load_baseline() -> list:
    return json.loads((FIXTURE_DIR / "baseline_raw.json").read_text(encoding="utf-8"))


def _load_delta() -> list:
    return json.loads((FIXTURE_DIR / "delta_raw.json").read_text(encoding="utf-8"))


def _make_connector(**kw) -> LangGraphConnector:
    defaults = {"graph_id": "test-graph", "source_instance": "test-instance"}
    defaults.update(kw)
    return LangGraphConnector(**defaults)


# ── Source Name ─────────────────────────────────────────────────────────────

class TestSourceName:
    def test_source_name_attribute(self):
        assert LangGraphConnector.source_name == "langgraph"

    def test_source_name_on_instance(self):
        c = _make_connector()
        assert c.source_name == "langgraph"


# ── LangSmith Run Format ───────────────────────────────────────────────────

class TestLangSmithRunFormat:
    def test_baseline_produces_5_records(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        assert len(records) == 5

    def test_record_types_match_run_types(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        types = [(r["content"]["run_type"], r["record_type"]) for r in records]
        assert types == [
            ("chain", "Event"),
            ("llm", "Claim"),
            ("tool", "Event"),
            ("retriever", "Document"),
            ("chain", "Event"),
        ]

    def test_record_ids_are_deterministic(self):
        c = _make_connector()
        ids_a = [r["record_id"] for r in c.to_canonical(_load_baseline())]
        ids_b = [r["record_id"] for r in c.to_canonical(_load_baseline())]
        assert ids_a == ids_b
        assert all(ids_a)  # none empty

    def test_provenance_uri_format(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        for rec in records:
            uri = rec["provenance"][0]["ref"]
            assert uri.startswith("langgraph://test-graph/")

    def test_confidence_varies_by_run_type(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        scores = {r["content"]["run_type"]: r["confidence"]["score"] for r in records}
        assert scores["llm"] < scores["tool"]
        assert scores["retriever"] < scores["tool"]

    def test_duration_computed_from_timestamps(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        # First record: 10:00:00.000 → 10:00:02.500 = 2500ms
        assert records[0]["content"]["duration_ms"] == 2500.0
        # Tool: 10:00:02.600 → 10:00:03.200 = 600ms
        assert records[2]["content"]["duration_ms"] == 600.0

    def test_links_from_triggers(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        # First record triggered by "start:agent" → link to __start__
        assert len(records[0]["links"]) == 1
        assert records[0]["links"][0]["rel"] == "derived_from"
        # Tool triggered by "agent" → link to agent node
        assert len(records[2]["links"]) == 1
        # LLM has no triggers → no links
        assert len(records[1]["links"]) == 0

    def test_step_in_content(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        steps = [r["content"]["step"] for r in records]
        assert steps == [1, 1, 2, 2, 3]

    def test_status_captured(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        assert all(r["content"]["status"] == "success" for r in records)

    def test_error_captured_in_delta(self):
        c = _make_connector()
        records = c.to_canonical(_load_delta())
        assert len(records) == 1
        assert "error" in records[0]["content"]
        assert "PermissionDenied" in records[0]["content"]["error"]
        assert records[0]["content"]["status"] == "error"


# ── astream_events Format ──────────────────────────────────────────────────

class TestAstreamEventsFormat:
    @pytest.fixture
    def events(self):
        """Minimal astream_events v2 trace."""
        return [
            {
                "event": "on_chain_start",
                "name": "LangGraph",
                "run_id": "run-graph-1",
                "parent_ids": [],
                "metadata": {"langgraph_step": 0, "langgraph_node": "__start__"},
                "data": {"input": {"query": "test"}},
            },
            {
                "event": "on_chain_end",
                "name": "LangGraph",
                "run_id": "run-graph-1",
                "parent_ids": [],
                "metadata": {"langgraph_step": 0, "langgraph_node": "__start__"},
                "data": {"output": {"query": "test"}},
            },
            {
                "event": "on_chat_model_start",
                "name": "ChatAnthropic",
                "run_id": "run-llm-1",
                "parent_ids": ["run-graph-1"],
                "metadata": {"langgraph_step": 1, "langgraph_node": "agent"},
                "data": {"input": {"messages": []}},
            },
            {
                "event": "on_chat_model_stream",
                "name": "ChatAnthropic",
                "run_id": "run-llm-1",
                "parent_ids": ["run-graph-1"],
                "metadata": {},
                "data": {"chunk": "token"},
            },
            {
                "event": "on_chat_model_end",
                "name": "ChatAnthropic",
                "run_id": "run-llm-1",
                "parent_ids": ["run-graph-1"],
                "metadata": {"langgraph_step": 1, "langgraph_node": "agent"},
                "data": {"output": {"content": "response"}},
            },
            {
                "event": "on_tool_start",
                "name": "search_tool",
                "run_id": "run-tool-1",
                "parent_ids": ["run-graph-1"],
                "metadata": {"langgraph_step": 2, "langgraph_node": "tools", "langgraph_triggers": ["agent"]},
                "data": {"input": {"query": "test query"}},
            },
            {
                "event": "on_tool_end",
                "name": "search_tool",
                "run_id": "run-tool-1",
                "parent_ids": ["run-graph-1"],
                "metadata": {"langgraph_step": 2, "langgraph_node": "tools", "langgraph_triggers": ["agent"]},
                "data": {"output": "search results"},
            },
        ]

    def test_events_produce_records(self, events):
        c = _make_connector()
        records = c.to_canonical(events)
        # start/end pairs: chain, llm, tool = 3 records (stream skipped)
        assert len(records) == 3

    def test_stream_events_skipped(self, events):
        c = _make_connector()
        records = c.to_canonical(events)
        run_types = [r["content"]["run_type"] for r in records]
        assert "stream" not in run_types

    def test_llm_mapped_to_claim(self, events):
        c = _make_connector()
        records = c.to_canonical(events)
        llm_records = [r for r in records if r["content"]["run_type"] == "llm"]
        assert len(llm_records) == 1
        assert llm_records[0]["record_type"] == "Claim"

    def test_tool_trigger_creates_link(self, events):
        c = _make_connector()
        records = c.to_canonical(events)
        tool_records = [r for r in records if r["content"]["run_type"] == "tool"]
        assert len(tool_records) == 1
        assert len(tool_records[0]["links"]) == 1
        assert tool_records[0]["links"][0]["rel"] == "derived_from"


# ── Nested Run Tree ────────────────────────────────────────────────────────

class TestNestedRunTree:
    def test_flatten_nested_tree(self):
        tree = {
            "id": "root",
            "name": "LangGraph",
            "run_type": "chain",
            "start_time": "2026-02-18T10:00:00Z",
            "end_time": "2026-02-18T10:00:05Z",
            "status": "success",
            "inputs": {},
            "outputs": {},
            "trace_id": "trace-1",
            "parent_run_id": None,
            "extra": {"metadata": {"langgraph_step": 0, "langgraph_node": "__start__"}},
            "child_runs": [
                {
                    "id": "child-1",
                    "name": "agent",
                    "run_type": "chain",
                    "start_time": "2026-02-18T10:00:01Z",
                    "end_time": "2026-02-18T10:00:03Z",
                    "status": "success",
                    "inputs": {"x": 1},
                    "outputs": {"y": 2},
                    "trace_id": "trace-1",
                    "parent_run_id": "root",
                    "extra": {"metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["start:agent"]}},
                    "child_runs": [],
                },
            ],
        }
        c = _make_connector()
        records = c.to_canonical(tree)
        assert len(records) == 2
        nodes = [r["content"]["node_name"] for r in records]
        assert "__start__" in nodes
        assert "agent" in nodes

    def test_child_runs_not_in_raw(self):
        tree = {
            "id": "root",
            "name": "LangGraph",
            "run_type": "chain",
            "start_time": "2026-02-18T10:00:00Z",
            "end_time": "2026-02-18T10:00:05Z",
            "status": "success",
            "inputs": {},
            "outputs": {},
            "trace_id": "trace-1",
            "parent_run_id": None,
            "extra": {"metadata": {}},
            "child_runs": [
                {
                    "id": "child-1",
                    "name": "agent",
                    "run_type": "chain",
                    "start_time": "2026-02-18T10:00:01Z",
                    "end_time": "2026-02-18T10:00:03Z",
                    "status": "success",
                    "inputs": {},
                    "outputs": {},
                    "trace_id": "trace-1",
                    "parent_run_id": "root",
                    "extra": {"metadata": {}},
                    "child_runs": [],
                },
            ],
        }
        c = _make_connector()
        flat = c._flatten_run_tree(tree)
        for run in flat:
            assert "child_runs" not in run


# ── Envelopes ──────────────────────────────────────────────────────────────

class TestEnvelopes:
    def test_to_envelopes_wraps_records(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        envelopes = c.to_envelopes(records)
        assert len(envelopes) == 5
        assert all(isinstance(e, RecordEnvelope) for e in envelopes)

    def test_all_envelopes_validate(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        envelopes = c.to_envelopes(records)
        for i, env in enumerate(envelopes):
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation errors at [{i}]: {errors}"

    def test_envelope_source_correct(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        envelopes = c.to_envelopes(records)
        for env in envelopes:
            assert env.source == "langgraph"
            assert env.source_instance == "test-instance"

    def test_envelope_hashes_present(self):
        c = _make_connector()
        records = c.to_canonical(_load_baseline())
        envelopes = c.to_envelopes(records)
        for env in envelopes:
            assert "raw_sha256" in env.hashes
            assert len(env.hashes["raw_sha256"]) == 64


# ── Edge Cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_list_returns_empty(self):
        c = _make_connector()
        assert c.to_canonical([]) == []

    def test_unrecognized_format_returns_empty(self):
        c = _make_connector()
        assert c.to_canonical([{"weird": "data"}]) == []

    def test_list_records_raises(self):
        c = _make_connector()
        with pytest.raises(NotImplementedError):
            c.list_records()

    def test_get_record_raises(self):
        c = _make_connector()
        with pytest.raises(NotImplementedError):
            c.get_record("some-id")

    def test_missing_timestamps_no_duration(self):
        run = {
            "id": "run-no-time",
            "name": "node",
            "run_type": "chain",
            "start_time": "",
            "end_time": "",
            "status": "success",
            "inputs": {},
            "outputs": {},
            "trace_id": "",
            "parent_run_id": None,
            "extra": {"metadata": {}},
        }
        c = _make_connector()
        records = c.to_canonical([run])
        assert len(records) == 1
        assert "duration_ms" not in records[0]["content"]

    def test_wrapper_dict_with_events_key(self):
        events = [
            {"event": "on_chain_start", "name": "g", "run_id": "r1", "metadata": {}, "data": {"input": {}}},
            {"event": "on_chain_end", "name": "g", "run_id": "r1", "metadata": {}, "data": {"output": {}}},
        ]
        c = _make_connector()
        records = c.to_canonical({"events": events})
        assert len(records) == 1
