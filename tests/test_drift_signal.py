"""Tests for core.drift_signal — drift signal collection and summarisation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.drift_signal import (  # noqa: E402
    DRIFT_TYPES,
    SEVERITY_ORDER,
    DriftBucket,
    DriftSignalCollector,
    DriftSummary,
)


def _make_event(
    drift_type="freshness",
    severity="yellow",
    fingerprint_key="AQ:freshness:geo",
    episode_id="ep-001",
    detected_at="2026-03-01T00:00:00Z",
    patch_type="ttl_change",
):
    return {
        "driftType": drift_type,
        "severity": severity,
        "fingerprint": {"key": fingerprint_key, "version": "1"},
        "episodeId": episode_id,
        "detectedAt": detected_at,
        "recommendedPatchType": patch_type,
    }


class TestConstants:
    def test_drift_types_frozen(self):
        assert isinstance(DRIFT_TYPES, frozenset)
        assert "freshness" in DRIFT_TYPES
        assert "time" in DRIFT_TYPES

    def test_severity_order(self):
        assert SEVERITY_ORDER["red"] > SEVERITY_ORDER["yellow"] > SEVERITY_ORDER["green"]


class TestDriftBucket:
    def test_defaults(self):
        b = DriftBucket(fingerprint_key="k", drift_type="freshness")
        assert b.count == 0
        assert b.worst_severity == "green"
        assert b.episode_ids == []


class TestDriftSignalCollector:
    def test_empty_collector(self):
        ds = DriftSignalCollector()
        assert ds.event_count == 0

    def test_ingest_single(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event()])
        assert ds.event_count == 1

    def test_ingest_multiple(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event(), _make_event(drift_type="time")])
        assert ds.event_count == 2

    def test_ingest_batch_then_more(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event()])
        ds.ingest([_make_event(drift_type="time")])
        assert ds.event_count == 2

    def test_summarise_total_signals(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event(), _make_event(drift_type="time")])
        summary = ds.summarise()
        assert summary.total_signals == 2

    def test_summarise_by_type(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(drift_type="freshness"),
            _make_event(drift_type="freshness"),
            _make_event(drift_type="time"),
        ])
        summary = ds.summarise()
        assert summary.by_type["freshness"] == 2
        assert summary.by_type["time"] == 1

    def test_summarise_by_severity(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(severity="yellow"),
            _make_event(severity="red"),
            _make_event(severity="yellow"),
        ])
        summary = ds.summarise()
        assert summary.by_severity["yellow"] == 2
        assert summary.by_severity["red"] == 1

    def test_fingerprint_bucketing(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-b"),
        ])
        summary = ds.summarise()
        fps = {b.fingerprint_key for b in summary.buckets}
        assert fps == {"fp-a", "fp-b"}

    def test_recurrence_counting(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-a"),
        ])
        summary = ds.summarise()
        bucket = [b for b in summary.buckets if b.fingerprint_key == "fp-a"][0]
        assert bucket.count == 3

    def test_severity_escalation(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a", severity="green"),
            _make_event(fingerprint_key="fp-a", severity="red"),
        ])
        summary = ds.summarise()
        bucket = [b for b in summary.buckets if b.fingerprint_key == "fp-a"][0]
        assert bucket.worst_severity == "red"

    def test_top_recurring(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-a"),
            _make_event(fingerprint_key="fp-b"),
        ])
        summary = ds.summarise()
        assert "fp-a" in summary.top_recurring

    def test_episode_ids_tracked(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a", episode_id="ep-1"),
            _make_event(fingerprint_key="fp-a", episode_id="ep-2"),
            _make_event(fingerprint_key="fp-a", episode_id="ep-1"),
        ])
        summary = ds.summarise()
        bucket = [b for b in summary.buckets if b.fingerprint_key == "fp-a"][0]
        assert set(bucket.episode_ids) == {"ep-1", "ep-2"}

    def test_to_json_round_trip(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event()])
        j = ds.to_json()
        data = json.loads(j)
        assert data["total_signals"] == 1

    def test_clear(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event()])
        ds.clear()
        assert ds.event_count == 0
        summary = ds.summarise()
        assert summary.total_signals == 0

    def test_camel_case_input_normalised(self):
        ds = DriftSignalCollector()
        ds.ingest([{
            "driftType": "freshness",
            "severity": "yellow",
            "fingerprint": {"key": "k1"},
            "episodeId": "ep-1",
        }])
        assert ds.event_count == 1

    def test_collected_at_iso(self):
        ds = DriftSignalCollector()
        ds.ingest([_make_event()])
        summary = ds.summarise()
        assert "T" in summary.collected_at

    def test_recommended_patches_tracked(self):
        ds = DriftSignalCollector()
        ds.ingest([
            _make_event(fingerprint_key="fp-a", patch_type="ttl_change"),
            _make_event(fingerprint_key="fp-a", patch_type="rate_limit"),
        ])
        summary = ds.summarise()
        bucket = [b for b in summary.buckets if b.fingerprint_key == "fp-a"][0]
        assert set(bucket.recommended_patches) == {"ttl_change", "rate_limit"}
