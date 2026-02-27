"""Shared test fixtures for DeepSigma core test suite."""

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_EPISODES_PATH = _REPO_ROOT / "src" / "core" / "examples" / "sample_episodes.json"
SAMPLE_DRIFT_PATH = _REPO_ROOT / "src" / "core" / "examples" / "sample_drift.json"


@pytest.fixture
def sample_episodes():
    """Load sample sealed episodes from the demo corpus."""
    return json.loads(SAMPLE_EPISODES_PATH.read_text())


@pytest.fixture
def sample_drift_events():
    """Load sample drift events from the demo corpus."""
    return json.loads(SAMPLE_DRIFT_PATH.read_text())


@pytest.fixture
def minimal_episode():
    """Factory fixture producing minimal valid episode dicts."""
    def _make(episode_id="ep-test-001", decision_type="AccountQuarantine", **overrides):
        ep = {
            "episodeId": episode_id,
            "decisionType": decision_type,
            "startedAt": "2026-02-01T12:00:00Z",
            "endedAt": "2026-02-01T12:00:01Z",
            "actions": [{
                "type": "quarantine",
                "blastRadiusTier": "account",
                "idempotencyKey": f"ik-{episode_id}",
                "targetRefs": ["acc-001"],
            }],
            "context": {
                "evidenceRefs": ["evidence-ref-001"],
                "ttlMs": 1000,
                "maxFeatureAgeMs": 500,
                "ttlBreachesCount": 0,
            },
            "outcome": {"code": "success"},
            "degrade": {"step": "none"},
            "verification": {"result": "pass"},
            "telemetry": {
                "endToEndMs": 80,
                "stageMs": {"context": 20, "plan": 20, "act": 20, "verify": 20},
                "p95Ms": 100, "p99Ms": 120, "jitterMs": 5,
                "fallbackUsed": False, "fallbackStep": "none",
                "hopCount": 1, "fanout": 1,
            },
            "seal": {
                "sealHash": f"sha256:{episode_id}",
                "sealedAt": "2026-02-01T12:00:01Z",
            },
            "sealedAt": "2026-02-01T12:00:01Z",
            "actor": {"type": "agent", "id": "test-agent"},
            "dteRef": {"decisionType": decision_type, "version": "1.0"},
            "plan": {"planner": "rules", "summary": "test plan"},
            "decisionWindowMs": 120,
        }
        ep.update(overrides)
        return ep
    return _make


@pytest.fixture
def minimal_drift():
    """Factory fixture producing minimal valid drift dicts."""
    def _make(drift_id="drift-test-001", episode_id="ep-test-001", **overrides):
        d = {
            "driftId": drift_id,
            "episodeId": episode_id,
            "driftType": "freshness",
            "severity": "yellow",
            "detectedAt": "2026-02-01T15:00:00Z",
            "fingerprint": {"key": "AQ:freshness:geo", "version": "1"},
            "recommendedPatchType": "ttl_change",
            "evidenceRefs": [],
        }
        d.update(overrides)
        return d
    return _make


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory with subdirectories for MG persistence."""
    (tmp_path / "episodes").mkdir()
    (tmp_path / "mg").mkdir()
    return tmp_path


@pytest.fixture
def coherence_pipeline(sample_episodes, sample_drift_events):
    """Build and return the full (dlr, rs, ds, mg) coherence pipeline."""
    from core import (
        DLRBuilder,
        DriftSignalCollector,
        MemoryGraph,
        ReflectionSession,
    )

    dlr = DLRBuilder()
    dlr.from_episodes(sample_episodes)

    rs = ReflectionSession("conftest-rs")
    rs.ingest(sample_episodes)

    ds = DriftSignalCollector()
    ds.ingest(sample_drift_events)

    mg = MemoryGraph()
    for ep in sample_episodes:
        mg.add_episode(ep)
    for d in sample_drift_events:
        mg.add_drift(d)

    return dlr, rs, ds, mg


# ── FEEDS fixtures ────────────────────────────────────────────────

FEEDS_FIXTURES_DIR = _REPO_ROOT / "src" / "core" / "fixtures" / "feeds"


@pytest.fixture
def feeds_golden_fixtures():
    """Load all FEEDS golden fixtures as a dict keyed by topic."""
    fixtures = {}
    for f in sorted(FEEDS_FIXTURES_DIR.glob("*_golden.json")):
        fixtures[f.stem.replace("_golden", "")] = json.loads(f.read_text())
    return fixtures


@pytest.fixture
def tmp_topics_root(tmp_path):
    """Temporary topics root directory for FEEDS bus testing."""
    from core.feeds.types import FeedTopic
    for topic in FeedTopic:
        for sub in ("inbox", "processing", "ack", "dlq"):
            (tmp_path / topic.value / sub).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def minimal_feed_envelope():
    """Factory fixture producing minimal valid FEEDS envelope dicts."""
    from core.feeds import build_envelope, FeedTopic

    def _make(topic=FeedTopic.TRUTH_SNAPSHOT, payload=None, **overrides):
        if payload is None:
            payload = {
                "snapshotId": "TS-test-001",
                "capturedAt": "2026-02-27T10:00:00Z",
                "claims": [{"claimId": "CLAIM-2026-0001"}],
                "evidenceSummary": "Test evidence.",
                "coherenceScore": 80,
                "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
            }
        env = build_envelope(
            topic=topic,
            payload=payload,
            packet_id="CP-2026-02-27-0001",
            producer="test-producer",
        )
        env.update(overrides)
        return env
    return _make
