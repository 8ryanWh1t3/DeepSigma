"""JRM test fixtures."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "fixtures" / "jrm"


@pytest.fixture
def sample_suricata_lines():
    """Load sample Suricata EVE lines."""
    return (FIXTURES_DIR / "suricata_eve_sample.jsonl").read_text().strip().splitlines()


@pytest.fixture
def sample_snort_lines():
    """Load sample Snort fast.log lines."""
    return (FIXTURES_DIR / "snort_fastlog_sample.txt").read_text().strip().splitlines()


@pytest.fixture
def sample_agent_lines():
    """Load sample copilot agent JSONL lines."""
    return (FIXTURES_DIR / "copilot_agent_sample.jsonl").read_text().strip().splitlines()


@pytest.fixture
def golden_jrm_event():
    """Load golden JRM event dict."""
    return json.loads((FIXTURES_DIR / "jrm_event_golden.json").read_text())


@pytest.fixture
def minimal_jrm_event():
    """Factory fixture producing minimal valid JRMEvent dicts."""
    def _make(event_id="JRM-TEST-001", source_system="suricata", **overrides):
        e = {
            "eventId": event_id,
            "sourceSystem": source_system,
            "eventType": "suricata_alert",
            "timestamp": "2026-02-28T10:00:00Z",
            "severity": "high",
            "actor": {"type": "host", "id": "10.0.0.1"},
            "object": {"type": "host", "id": "10.0.0.2"},
            "action": "alert:sid=2010935:rev=6",
            "confidence": 0.85,
            "evidenceHash": "sha256:" + "a" * 64,
            "rawPointer": "inline:sha256:" + "a" * 64,
            "environmentId": "test-env",
            "assumptions": [],
        }
        e.update(overrides)
        return e
    return _make


@pytest.fixture
def tmp_jrm_output(tmp_path):
    """Temporary output directory for JRM packets."""
    out = tmp_path / "jrm_packets"
    out.mkdir()
    return out
