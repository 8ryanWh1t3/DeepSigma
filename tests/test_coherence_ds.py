"""Unit tests for coherence_ops.ds — Drift Signal Collector (Decision Scaffold)."""
import json
import pytest
from coherence_ops.ds import DriftSignalCollector, DriftBucket, DriftSummary


def _drift(drift_type="freshness", severity="yellow", fp_key="AQ:freshness:geo",
           episode_id="ep-1", patch_type="ttl_change", detected_at="2026-02-12T15:00:00Z"):
    """Minimal drift event dict for testing."""
    return {
        "driftType": drift_type,
        "severity": severity,
        "fingerprint": {"key": fp_key},
        "episodeId": episode_id,
        "detectedAt": detected_at,
        "recommendedPatchType": patch_type,
    }


class TestDriftSignalCollector:
    """DriftSignalCollector aggregates DTE + degrade ladder drift data."""

    def test_ingest_single(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift()])
        assert ds.event_count == 1

    def test_ingest_batch(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift(), _drift(episode_id="ep-2"), _drift(episode_id="ep-3")])
        assert ds.event_count == 3

    def test_summary_type(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift()])
        summary = ds.summarise()
        assert isinstance(summary, DriftSummary)

    def test_summary_total_signals(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift(), _drift(episode_id="ep-2")])
        assert ds.summarise().total_signals == 2

    def test_by_type_counts(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(drift_type="freshness"),
            _drift(drift_type="freshness"),
            _drift(drift_type="time"),
        ])
        summary = ds.summarise()
        assert summary.by_type["freshness"] == 2
        assert summary.by_type["time"] == 1

    def test_by_severity_counts(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(severity="red"),
            _drift(severity="yellow"),
            _drift(severity="red"),
        ])
        summary = ds.summarise()
        assert summary.by_severity["red"] == 2
        assert summary.by_severity["yellow"] == 1

    def test_fingerprint_bucketing(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(fp_key="AQ:freshness:geo", severity="yellow"),
            _drift(fp_key="AQ:freshness:geo", severity="red"),
        ])
        summary = ds.summarise()
        geo_buckets = [b for b in summary.buckets if b.fingerprint_key == "AQ:freshness:geo"]
        assert len(geo_buckets) == 1
        assert geo_buckets[0].count == 2
        assert geo_buckets[0].worst_severity == "red"

    def test_bucket_first_last_seen(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(fp_key="key1", detected_at="2026-02-12T10:00:00Z"),
            _drift(fp_key="key1", detected_at="2026-02-12T12:00:00Z"),
        ])
        summary = ds.summarise()
        bucket = summary.buckets[0]
        assert bucket.first_seen == "2026-02-12T10:00:00Z"
        assert bucket.last_seen == "2026-02-12T12:00:00Z"

    def test_top_recurring(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(fp_key="recurring-key"),
            _drift(fp_key="recurring-key"),
            _drift(fp_key="one-off"),
        ])
        summary = ds.summarise()
        assert "recurring-key" in summary.top_recurring
        assert "one-off" not in summary.top_recurring

    def test_recommended_patches_collected(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _drift(fp_key="k1", patch_type="ttl_change"),
            _drift(fp_key="k1", patch_type="budget_increase"),
        ])
        summary = ds.summarise()
        bucket = [b for b in summary.buckets if b.fingerprint_key == "k1"][0]
        assert "ttl_change" in bucket.recommended_patches
        assert "budget_increase" in bucket.recommended_patches

    def test_clear(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift()])
        assert ds.event_count == 1
        ds.clear()
        assert ds.event_count == 0

    def test_to_json_valid(self):
        ds = DriftSignalCollector()
        ds.ingest([_drift()])
        raw = ds.to_json()
        data = json.loads(raw)
        assert data["total_signals"] == 1
        assert "buckets" in data

    def test_empty_summary(self):
        ds = DriftSignalCollector()
        summary = ds.summarise()
        assert summary.total_signals == 0
        assert summary.buckets == []
