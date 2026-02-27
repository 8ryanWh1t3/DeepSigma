"""Tests for FEEDS envelope builder and payload hashing."""

import json

import pytest

from core.feeds import build_envelope, compute_payload_hash, FeedTopic, Classification
from core.feeds.types import TOPIC_TO_RECORD, RecordType
from core.schema_validator import clear_cache, validate


@pytest.fixture(autouse=True)
def _clear_schema_cache():
    clear_cache()
    yield
    clear_cache()


SAMPLE_PAYLOAD = {
    "snapshotId": "TS-test-001",
    "capturedAt": "2026-02-27T10:00:00Z",
    "claims": [{"claimId": "CLAIM-2026-0001"}],
    "evidenceSummary": "Test evidence summary for envelope tests.",
    "coherenceScore": 80,
    "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
}


class TestComputePayloadHash:
    def test_deterministic(self):
        h1 = compute_payload_hash(SAMPLE_PAYLOAD)
        h2 = compute_payload_hash(SAMPLE_PAYLOAD)
        assert h1 == h2

    def test_format(self):
        h = compute_payload_hash(SAMPLE_PAYLOAD)
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_different_payloads_different_hashes(self):
        h1 = compute_payload_hash(SAMPLE_PAYLOAD)
        h2 = compute_payload_hash({"different": "payload"})
        assert h1 != h2

    def test_key_order_irrelevant(self):
        """Canonical JSON sorts keys, so insertion order doesn't matter."""
        a = {"z": 1, "a": 2}
        b = {"a": 2, "z": 1}
        assert compute_payload_hash(a) == compute_payload_hash(b)


class TestBuildEnvelope:
    def test_envelope_validates_against_schema(self):
        env = build_envelope(
            topic=FeedTopic.TRUTH_SNAPSHOT,
            payload=SAMPLE_PAYLOAD,
            packet_id="CP-2026-02-27-0001",
            producer="test-producer",
        )
        result = validate(env, "feeds_event_envelope")
        assert result.valid, f"Envelope validation errors: {result.errors}"

    def test_auto_generates_fields(self):
        env = build_envelope(
            topic=FeedTopic.TRUTH_SNAPSHOT,
            payload=SAMPLE_PAYLOAD,
            packet_id="CP-2026-02-27-0001",
            producer="test-producer",
        )
        assert env["eventId"]  # auto-generated UUID
        assert env["uid"] == env["eventId"]
        assert env["createdAt"]
        assert env["payloadHash"].startswith("sha256:")

    def test_topic_record_mapping(self):
        for topic, expected_rt in TOPIC_TO_RECORD.items():
            env = build_envelope(
                topic=topic,
                payload={"test": True},
                packet_id="CP-2026-02-27-0001",
                producer="test",
            )
            assert env["recordType"] == expected_rt.value

    def test_explicit_fields_preserved(self):
        env = build_envelope(
            topic=FeedTopic.DRIFT_SIGNAL,
            payload={"test": True},
            packet_id="CP-2026-02-27-0001",
            producer="test",
            event_id="custom-id",
            uid="custom-uid",
            human_id="HR-001",
            subtype="authority_mismatch",
            classification=Classification.LEVEL_3,
            sequence=42,
        )
        assert env["eventId"] == "custom-id"
        assert env["uid"] == "custom-uid"
        assert env["humanId"] == "HR-001"
        assert env["subtype"] == "authority_mismatch"
        assert env["classification"] == "LEVEL_3"
        assert env["sequence"] == 42

    def test_string_topic_accepted(self):
        env = build_envelope(
            topic="truth_snapshot",
            payload=SAMPLE_PAYLOAD,
            packet_id="CP-2026-02-27-0001",
            producer="test",
        )
        assert env["topic"] == "truth_snapshot"
        assert env["recordType"] == "TS"

    def test_payload_hash_matches_compute(self):
        env = build_envelope(
            topic=FeedTopic.TRUTH_SNAPSHOT,
            payload=SAMPLE_PAYLOAD,
            packet_id="CP-2026-02-27-0001",
            producer="test",
        )
        assert env["payloadHash"] == compute_payload_hash(SAMPLE_PAYLOAD)
