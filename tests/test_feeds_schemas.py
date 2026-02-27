"""Tests for FEEDS schema validation — golden fixtures and negative cases."""

import json
from pathlib import Path

import pytest

from core.schema_validator import clear_cache, validate

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "src" / "core" / "fixtures" / "feeds"

GOLDEN_FILES = [
    "ts_golden.json",
    "als_golden.json",
    "dlr_golden.json",
    "ds_golden.json",
    "ce_golden.json",
    "manifest_golden.json",
]


@pytest.fixture(autouse=True)
def _clear_schema_cache():
    clear_cache()
    yield
    clear_cache()


class TestGoldenFixturesValidate:
    """Every golden fixture should pass envelope + payload validation."""

    @pytest.mark.parametrize("filename", GOLDEN_FILES)
    def test_golden_validates_envelope(self, filename):
        event = json.loads((FIXTURES_DIR / filename).read_text())
        result = validate(event, "feeds_event_envelope")
        assert result.valid, f"{filename} envelope errors: {result.errors}"

    @pytest.mark.parametrize(
        "filename,payload_schema",
        [
            ("ts_golden.json", "truth_snapshot"),
            ("als_golden.json", "authority_slice"),
            ("dlr_golden.json", "decision_lineage"),
            ("ds_golden.json", "drift_signal"),
            ("ce_golden.json", "canon_entry"),
            ("manifest_golden.json", "packet_index"),
        ],
    )
    def test_golden_validates_payload(self, filename, payload_schema):
        event = json.loads((FIXTURES_DIR / filename).read_text())
        result = validate(event["payload"], payload_schema)
        assert result.valid, f"{filename} payload errors: {result.errors}"


class TestNegativeCases:
    """Schema validation should reject malformed events."""

    def test_missing_required_field(self):
        event = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())
        del event["eventId"]
        result = validate(event, "feeds_event_envelope")
        assert not result.valid

    def test_bad_classification(self):
        event = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())
        event["classification"] = "TOP_SECRET"
        result = validate(event, "feeds_event_envelope")
        assert not result.valid

    def test_bad_topic(self):
        event = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())
        event["topic"] = "invalid_topic"
        result = validate(event, "feeds_event_envelope")
        assert not result.valid

    def test_bad_payload_hash_format(self):
        event = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())
        event["payloadHash"] = "md5:abc123"
        result = validate(event, "feeds_event_envelope")
        assert not result.valid

    def test_bad_packet_id_format(self):
        event = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())
        event["packetId"] = "BAD-FORMAT"
        result = validate(event, "feeds_event_envelope")
        assert not result.valid

    def test_payload_missing_required(self):
        """Payload-level validation catches missing required fields."""
        payload = json.loads((FIXTURES_DIR / "ts_golden.json").read_text())["payload"]
        del payload["snapshotId"]
        result = validate(payload, "truth_snapshot")
        assert not result.valid

    def test_drift_signal_bad_type(self):
        payload = json.loads((FIXTURES_DIR / "ds_golden.json").read_text())["payload"]
        payload["driftType"] = "nonexistent_type"
        result = validate(payload, "drift_signal")
        assert not result.valid

    def test_canon_entry_bad_id_format(self):
        payload = json.loads((FIXTURES_DIR / "ce_golden.json").read_text())["payload"]
        payload["canonId"] = "BAD-ID"
        result = validate(payload, "canon_entry")
        assert not result.valid
