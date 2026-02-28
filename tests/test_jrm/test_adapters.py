"""Tests for JRM adapters."""

from __future__ import annotations

from core.jrm.adapters import get_adapter, list_adapters
from core.jrm.adapters.suricata_eve import SuricataEVEAdapter
from core.jrm.adapters.snort_fastlog import SnortFastlogAdapter
from core.jrm.adapters.copilot_agent import CopilotAgentAdapter
from core.jrm.types import EventType, Severity


class TestRegistry:
    def test_list_adapters(self):
        names = list_adapters()
        assert "suricata_eve" in names
        assert "snort_fastlog" in names
        assert "copilot_agent" in names

    def test_get_adapter(self):
        cls = get_adapter("suricata_eve")
        assert cls is SuricataEVEAdapter

    def test_get_adapter_unknown(self):
        import pytest
        with pytest.raises(KeyError, match="Unknown adapter"):
            get_adapter("nonexistent")


class TestSuricataEVEAdapter:
    def test_parse_alert(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        event = adapter.parse_line(sample_suricata_lines[0], 0)
        assert event is not None
        assert event.event_type == EventType.SURICATA_ALERT
        assert event.severity == Severity.CRITICAL
        assert event.metadata["signature_id"] == 2010935
        assert event.evidence_hash.startswith("sha256:")
        assert len(event.evidence_hash) == 71  # sha256: + 64 hex

    def test_parse_dns(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        event = adapter.parse_line(sample_suricata_lines[1], 1)
        assert event is not None
        assert event.event_type == EventType.SURICATA_DNS
        assert event.severity == Severity.INFO

    def test_parse_http(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        event = adapter.parse_line(sample_suricata_lines[2], 2)
        assert event is not None
        assert event.event_type == EventType.SURICATA_HTTP

    def test_parse_flow(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        event = adapter.parse_line(sample_suricata_lines[3], 3)
        assert event is not None
        assert event.event_type == EventType.SURICATA_FLOW

    def test_malformed_json(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        # Line 7 (0-indexed) is malformed
        event = adapter.parse_line(sample_suricata_lines[7], 7)
        assert event is not None
        assert event.event_type == EventType.MALFORMED
        assert event.raw_bytes == sample_suricata_lines[7].encode("utf-8")

    def test_empty_line(self):
        adapter = SuricataEVEAdapter()
        assert adapter.parse_line("", 0) is None
        assert adapter.parse_line("   ", 0) is None

    def test_parse_stream(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        events = list(adapter.parse_stream(iter(sample_suricata_lines)))
        assert len(events) == 12  # 12 non-empty lines (including malformed)
        malformed = [e for e in events if e.event_type == EventType.MALFORMED]
        assert len(malformed) == 1

    def test_conflicting_revs(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        events = list(adapter.parse_stream(iter(sample_suricata_lines)))
        alerts_2010935 = [
            e for e in events
            if e.metadata.get("signature_id") == 2010935
        ]
        revs = {e.metadata.get("rev") for e in alerts_2010935}
        assert len(revs) > 1  # Should have both rev 6 and rev 7

    def test_ipv6(self, sample_suricata_lines):
        adapter = SuricataEVEAdapter()
        event = adapter.parse_line(sample_suricata_lines[6], 6)
        assert event is not None
        assert event.actor["ip"] == "fe80::1"


class TestSnortFastlogAdapter:
    def test_parse_alert(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        event = adapter.parse_line(sample_snort_lines[0], 0)
        assert event is not None
        assert event.event_type == EventType.SNORT_ALERT
        assert event.severity == Severity.CRITICAL
        assert event.metadata["sid"] == "2010935"
        assert event.actor["ip"] == "10.0.0.5"
        assert event.actor["port"] == 54321
        assert event.object["ip"] == "192.168.1.100"

    def test_parse_medium_priority(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        event = adapter.parse_line(sample_snort_lines[1], 1)
        assert event is not None
        assert event.severity == Severity.MEDIUM

    def test_parse_low_priority(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        event = adapter.parse_line(sample_snort_lines[8], 8)
        assert event is not None
        assert event.severity == Severity.LOW

    def test_malformed(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        event = adapter.parse_line(sample_snort_lines[5], 5)
        assert event is not None
        assert event.event_type == EventType.MALFORMED

    def test_parse_stream(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        events = list(adapter.parse_stream(iter(sample_snort_lines)))
        assert len(events) == 10  # 10 non-empty lines
        malformed = [e for e in events if e.event_type == EventType.MALFORMED]
        assert len(malformed) == 1

    def test_evidence_hash_format(self, sample_snort_lines):
        adapter = SnortFastlogAdapter()
        event = adapter.parse_line(sample_snort_lines[0], 0)
        assert event.evidence_hash.startswith("sha256:")
        assert len(event.evidence_hash) == 71


class TestCopilotAgentAdapter:
    def test_parse_prompt(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[0], 0)
        assert event is not None
        assert event.event_type == EventType.AGENT_PROMPT
        assert event.severity == Severity.INFO
        assert event.actor["id"] == "agent-alpha"
        assert event.action == "prompt"

    def test_parse_tool_call(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[1], 1)
        assert event is not None
        assert event.event_type == EventType.AGENT_TOOL_CALL
        assert "query_logs" in event.action

    def test_parse_response(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[2], 2)
        assert event is not None
        assert event.event_type == EventType.AGENT_RESPONSE

    def test_parse_guardrail(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[5], 5)
        assert event is not None
        assert event.event_type == EventType.AGENT_GUARDRAIL
        assert event.severity == Severity.HIGH
        assert "guardrail:requires_approval" in event.assumptions

    def test_malformed(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[11], 11)
        assert event is not None
        assert event.event_type == EventType.MALFORMED

    def test_parse_stream(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        events = list(adapter.parse_stream(iter(sample_agent_lines)))
        assert len(events) == 13  # 13 non-empty lines
        malformed = [e for e in events if e.event_type == EventType.MALFORMED]
        assert len(malformed) == 1

    def test_confidence_preserved(self, sample_agent_lines):
        adapter = CopilotAgentAdapter()
        event = adapter.parse_line(sample_agent_lines[0], 0)
        assert event.confidence == 0.9
