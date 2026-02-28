"""Tests for JRM JSON Schema validation."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "schemas" / "jrm"
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "fixtures" / "jrm"


@pytest.fixture
def core_schema():
    return json.loads((SCHEMAS_DIR / "jrm_core.schema.json").read_text())


@pytest.fixture
def packet_schema():
    return json.loads((SCHEMAS_DIR / "jrm_packet.schema.json").read_text())


class TestCoreSchema:
    def test_golden_event_validates(self, core_schema, golden_jrm_event):
        jsonschema.validate(golden_jrm_event, core_schema)

    def test_minimal_event_validates(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event()
        jsonschema.validate(event, core_schema)

    def test_missing_required_field(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event()
        del event["eventId"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(event, core_schema)

    def test_invalid_severity(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event(severity="ultra")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(event, core_schema)

    def test_invalid_event_type(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event(eventType="bogus_type")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(event, core_schema)

    def test_invalid_evidence_hash(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event(evidenceHash="md5:abc123")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(event, core_schema)

    def test_confidence_range(self, core_schema, minimal_jrm_event):
        event = minimal_jrm_event(confidence=1.5)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(event, core_schema)

    def test_all_event_types_valid(self, core_schema, minimal_jrm_event):
        from core.jrm.types import EventType
        for et in EventType:
            event = minimal_jrm_event(eventType=et.value)
            jsonschema.validate(event, core_schema)


class TestPacketSchema:
    def test_valid_manifest(self, packet_schema):
        manifest = {
            "packetName": "JRM_X_PACKET_SOC_EAST_20260228T100000_20260228T101000_part01",
            "environmentId": "SOC_EAST",
            "windowStart": "2026-02-28T10:00:00Z",
            "windowEnd": "2026-02-28T10:10:00Z",
            "part": 1,
            "files": {
                "truth_snapshot.json": "sha256:" + "a" * 64,
                "authority_slice.json": "sha256:" + "b" * 64,
                "decision_lineage.jsonl": "sha256:" + "c" * 64,
                "drift_signal.jsonl": "sha256:" + "d" * 64,
                "memory_graph.json": "sha256:" + "e" * 64,
                "canon_entry.json": "sha256:" + "f" * 64,
            },
            "eventCount": 100,
            "sizeBytes": 50000,
            "createdAt": "2026-02-28T10:10:01Z",
        }
        jsonschema.validate(manifest, packet_schema)

    def test_missing_file(self, packet_schema):
        manifest = {
            "packetName": "JRM_X_PACKET_test_20260228_20260228_part01",
            "environmentId": "test",
            "windowStart": "2026-02-28T10:00:00Z",
            "windowEnd": "2026-02-28T10:10:00Z",
            "part": 1,
            "files": {
                "truth_snapshot.json": "sha256:" + "a" * 64,
                # missing other files
            },
            "eventCount": 10,
            "sizeBytes": 1000,
            "createdAt": "2026-02-28T10:10:01Z",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, packet_schema)

    def test_invalid_packet_name(self, packet_schema):
        manifest = {
            "packetName": "BAD_NAME",
            "environmentId": "test",
            "windowStart": "2026-02-28T10:00:00Z",
            "windowEnd": "2026-02-28T10:10:00Z",
            "part": 1,
            "files": {
                "truth_snapshot.json": "sha256:" + "a" * 64,
                "authority_slice.json": "sha256:" + "b" * 64,
                "decision_lineage.jsonl": "sha256:" + "c" * 64,
                "drift_signal.jsonl": "sha256:" + "d" * 64,
                "memory_graph.json": "sha256:" + "e" * 64,
                "canon_entry.json": "sha256:" + "f" * 64,
            },
            "eventCount": 10,
            "sizeBytes": 1000,
            "createdAt": "2026-02-28T10:10:01Z",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, packet_schema)
