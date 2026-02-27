"""Tests for LangGraphConnector."""
from __future__ import annotations

import pytest

from langchain_deepsigma.langgraph_connector import LangGraphConnector


@pytest.fixture
def connector():
    return LangGraphConnector(graph_id="test-graph")


@pytest.fixture
def astream_events():
    """Minimal astream_events v2 trace."""
    return [
        {
            "event": "on_chain_start",
            "name": "agent",
            "run_id": "run-001",
            "parent_ids": [],
            "metadata": {"langgraph_node": "agent", "langgraph_step": 1},
            "data": {"input": "hello"},
        },
        {
            "event": "on_chain_end",
            "name": "agent",
            "run_id": "run-001",
            "parent_ids": [],
            "metadata": {"langgraph_node": "agent", "langgraph_step": 1},
            "data": {"output": "world"},
        },
    ]


@pytest.fixture
def run_tree():
    """Minimal run tree trace."""
    return {
        "run_type": "chain",
        "name": "root",
        "id": "root-001",
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": "2026-01-01T00:00:01Z",
        "extra": {"metadata": {"langgraph_node": "root"}},
        "inputs": {"query": "test"},
        "outputs": {"answer": "result"},
        "child_runs": [
            {
                "run_type": "llm",
                "name": "gpt",
                "id": "llm-001",
                "start_time": "2026-01-01T00:00:00.100Z",
                "end_time": "2026-01-01T00:00:00.500Z",
                "extra": {"metadata": {"langgraph_node": "generator"}},
                "inputs": {"prompt": "test"},
                "outputs": {"text": "answer"},
                "child_runs": [],
            },
        ],
    }


class TestLangGraphConnector:

    def test_to_canonical_astream_events(self, connector, astream_events):
        records = connector.to_canonical(astream_events)
        assert len(records) == 1
        assert records[0]["record_type"] == "Event"
        assert records[0]["content"]["node_name"] == "agent"

    def test_to_canonical_run_tree(self, connector, run_tree):
        records = connector.to_canonical(run_tree)
        assert len(records) == 2
        types = {r["content"]["run_type"] for r in records}
        assert "chain" in types
        assert "llm" in types

    def test_to_canonical_flat_runs(self, connector):
        flat = [
            {"run_type": "tool", "name": "calc", "id": "t-1",
             "extra": {"metadata": {}}, "inputs": {}, "outputs": {}},
        ]
        records = connector.to_canonical(flat)
        assert len(records) == 1
        assert records[0]["record_type"] == "Event"

    def test_to_canonical_empty(self, connector):
        assert connector.to_canonical([]) == []

    def test_record_has_provenance(self, connector, astream_events):
        records = connector.to_canonical(astream_events)
        prov = records[0]["provenance"]
        assert len(prov) == 1
        assert "langgraph://test-graph/agent" in prov[0]["ref"]

    def test_confidence_mapping(self, connector):
        flat = [
            {"run_type": "llm", "name": "gen", "id": "l-1",
             "extra": {"metadata": {}}, "inputs": {}, "outputs": {}},
        ]
        records = connector.to_canonical(flat)
        assert records[0]["confidence"]["score"] == 0.75

    def test_to_agent_session_decisions(self, connector, astream_events):
        decisions = connector.to_agent_session_decisions(astream_events)
        assert len(decisions) == 1
        assert decisions[0]["action"] == "chain"
        assert decisions[0]["actor"]["id"] == "test-graph"

    def test_list_records_raises(self, connector):
        with pytest.raises(NotImplementedError):
            connector.list_records()

    def test_get_record_raises(self, connector):
        with pytest.raises(NotImplementedError):
            connector.get_record("x")
