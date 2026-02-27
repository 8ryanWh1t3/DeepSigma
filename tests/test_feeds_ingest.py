"""Tests for FEEDS ingest orchestrator — happy path, failures, atomic behavior."""

import json
from pathlib import Path

import pytest

from core.feeds import FeedTopic, compute_payload_hash
from core.feeds.ingest import IngestOrchestrator, IngestResult


# ── Helpers ───────────────────────────────────────────────────────

def _make_ts_payload():
    return {
        "snapshotId": "TS-ingest-001",
        "capturedAt": "2026-02-27T10:00:00Z",
        "claims": [{"claimId": "CLAIM-2026-0001"}],
        "evidenceSummary": "Ingest test evidence.",
        "coherenceScore": 80,
        "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
    }


def _make_ds_payload():
    return {
        "driftId": "DS-ingest-001",
        "driftType": "freshness",
        "severity": "yellow",
        "detectedAt": "2026-02-27T11:00:00Z",
        "evidenceRefs": ["ref-001"],
        "recommendedPatchType": "ttl_change",
        "fingerprint": {"key": "ingest:test", "version": "1"},
    }


def _make_als_payload():
    return {
        "sliceId": "ALS-ingest-001",
        "authoritySource": "governance-engine",
        "authorityRole": "policy-owner",
        "scope": "security-operations",
        "claimsBlessed": ["CLAIM-2026-0001"],
        "effectiveAt": "2026-02-27T09:00:00Z",
        "seal": {"hash": "sha256:als", "sealedAt": "2026-02-27T09:00:01Z", "version": 1},
    }


def _make_packet_index(packet_id):
    return {
        "packetId": packet_id,
        "createdAt": "2026-02-27T12:00:00Z",
        "producer": "test-ingest",
        "artifactManifest": [],
        "totalEvents": 0,
        "seal": {"hash": "sha256:pi", "sealedAt": "2026-02-27T12:00:01Z", "version": 1},
    }


def _build_packet_dir(tmp_path, packet_id="CP-2026-02-27-0001", artifacts=None):
    """Build a packet directory with manifest and artifact files."""
    packet_dir = tmp_path / "packet"
    packet_dir.mkdir()

    manifest = {"packetId": packet_id}

    if artifacts is None:
        # Default: TS + DS + packet_index
        ts = _make_ts_payload()
        ds = _make_ds_payload()
        pi = _make_packet_index(packet_id)

        (packet_dir / "truth_snapshot.json").write_text(json.dumps(ts))
        (packet_dir / "drift_signal.json").write_text(json.dumps(ds))

        manifest["artifacts"] = {
            "truth_snapshot": {"file": "truth_snapshot.json", "hash": compute_payload_hash(ts)},
            "drift_signal": {"file": "drift_signal.json", "hash": compute_payload_hash(ds)},
        }
        manifest["packetIndex"] = pi
    else:
        manifest["artifacts"] = artifacts

    (packet_dir / "manifest.json").write_text(json.dumps(manifest))
    return packet_dir


# ── Tests ─────────────────────────────────────────────────────────

class TestIngestHappyPath:
    def test_ingests_packet_successfully(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(packet_dir)

        assert result.success
        assert result.packet_id == "CP-2026-02-27-0001"
        assert result.events_published >= 2  # at least TS + DS
        assert result.errors == []

    def test_events_land_in_correct_inboxes(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root)
        orch.ingest(packet_dir)

        ts_inbox = tmp_topics_root / "truth_snapshot" / "inbox"
        ds_inbox = tmp_topics_root / "drift_signal" / "inbox"
        assert len(list(ts_inbox.glob("*.json"))) == 1
        assert len(list(ds_inbox.glob("*.json"))) == 1

    def test_events_are_valid_envelopes(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root)
        orch.ingest(packet_dir)

        from core.feeds.validate import validate_feed_event
        ts_inbox = tmp_topics_root / "truth_snapshot" / "inbox"
        for f in ts_inbox.glob("*.json"):
            event = json.loads(f.read_text())
            result = validate_feed_event(event)
            assert result.valid, f"Event invalid: {result.errors}"

    def test_classification_preserved(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root, classification="LEVEL_3")
        orch.ingest(packet_dir)

        ts_inbox = tmp_topics_root / "truth_snapshot" / "inbox"
        for f in ts_inbox.glob("*.json"):
            event = json.loads(f.read_text())
            assert event["classification"] == "LEVEL_3"

    def test_packet_index_included(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(packet_dir)

        pi_inbox = tmp_topics_root / "packet_index" / "inbox"
        assert len(list(pi_inbox.glob("*.json"))) == 1


class TestIngestFailures:
    def test_missing_manifest(self, tmp_topics_root, tmp_path):
        empty_dir = tmp_path / "empty_packet"
        empty_dir.mkdir()
        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(empty_dir)

        assert not result.success
        assert any("manifest.json" in e for e in result.errors)

    def test_missing_artifact_emits_process_gap(self, tmp_topics_root, tmp_path):
        packet_dir = tmp_path / "bad_packet"
        packet_dir.mkdir()
        manifest = {
            "packetId": "CP-2026-02-27-9999",
            "artifacts": {
                "truth_snapshot": {"file": "nonexistent.json", "hash": "sha256:bad"},
            },
        }
        (packet_dir / "manifest.json").write_text(json.dumps(manifest))

        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(packet_dir)

        assert not result.success
        assert result.drift_signal_id is not None
        assert any("Missing artifact" in e for e in result.errors)

    def test_hash_mismatch_emits_process_gap(self, tmp_topics_root, tmp_path):
        packet_dir = tmp_path / "tampered_packet"
        packet_dir.mkdir()

        ts = _make_ts_payload()
        (packet_dir / "truth_snapshot.json").write_text(json.dumps(ts))

        manifest = {
            "packetId": "CP-2026-02-27-8888",
            "artifacts": {
                "truth_snapshot": {"file": "truth_snapshot.json", "hash": "sha256:tampered_hash_0000000000000000000000000000000000000000000000000000000000"},
            },
        }
        (packet_dir / "manifest.json").write_text(json.dumps(manifest))

        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(packet_dir)

        assert not result.success
        assert any("Hash mismatch" in e for e in result.errors)
        assert result.drift_signal_id is not None

    def test_drift_signal_written_to_inbox_on_failure(self, tmp_topics_root, tmp_path):
        empty_dir = tmp_path / "fail_packet"
        empty_dir.mkdir()
        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(empty_dir)

        # PROCESS_GAP DS should be in drift_signal inbox
        ds_inbox = tmp_topics_root / "drift_signal" / "inbox"
        ds_files = list(ds_inbox.glob("*.json"))
        assert len(ds_files) >= 1
        ds_event = json.loads(ds_files[0].read_text())
        assert ds_event["payload"]["driftType"] == "process_gap"


class TestIngestAtomicBehavior:
    def test_staging_cleaned_up_on_success(self, tmp_topics_root, tmp_path):
        packet_dir = _build_packet_dir(tmp_path)
        orch = IngestOrchestrator(tmp_topics_root)
        orch.ingest(packet_dir)

        staging = tmp_topics_root / ".staging"
        if staging.exists():
            # Should be empty (packet subdir removed)
            assert list(staging.iterdir()) == []

    def test_staging_cleaned_up_on_failure(self, tmp_topics_root, tmp_path):
        packet_dir = tmp_path / "bad"
        packet_dir.mkdir()
        manifest = {
            "packetId": "CP-2026-02-27-7777",
            "artifacts": {
                "truth_snapshot": {"file": "missing.json", "hash": "sha256:x"},
            },
        }
        (packet_dir / "manifest.json").write_text(json.dumps(manifest))

        orch = IngestOrchestrator(tmp_topics_root)
        orch.ingest(packet_dir)

        staging = tmp_topics_root / ".staging"
        if staging.exists():
            assert list(staging.iterdir()) == []


class TestIngestAutoDetect:
    def test_auto_detects_topics_without_artifacts_key(self, tmp_topics_root, tmp_path):
        """When manifest has no 'artifacts' key, auto-detect from files present."""
        packet_dir = tmp_path / "auto_packet"
        packet_dir.mkdir()

        ts = _make_ts_payload()
        als = _make_als_payload()
        pi = _make_packet_index("CP-2026-02-27-5555")

        (packet_dir / "truth_snapshot.json").write_text(json.dumps(ts))
        (packet_dir / "authority_slice.json").write_text(json.dumps(als))

        manifest = {"packetId": "CP-2026-02-27-5555", "packetIndex": pi}
        (packet_dir / "manifest.json").write_text(json.dumps(manifest))

        orch = IngestOrchestrator(tmp_topics_root)
        result = orch.ingest(packet_dir)

        assert result.success
        assert result.events_published >= 2  # TS + ALS + packet_index
