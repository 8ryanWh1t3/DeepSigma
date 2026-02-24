"""Shared test fixtures for DeepSigma test suite."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

# Ensure imports resolve
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SAMPLE_EPISODES_PATH = SRC_ROOT / "core" / "examples" / "sample_episodes.json"
SAMPLE_DRIFT_PATH = SRC_ROOT / "core" / "examples" / "sample_drift.json"
POLICY_PACK_PATH = REPO_ROOT / "docs" / "policy_packs" / "packs" / "demo_policy_pack_v1.json"


@pytest.fixture
def sample_episodes():
    """Load sample sealed episodes from the demo corpus."""
    return json.loads(SAMPLE_EPISODES_PATH.read_text())


@pytest.fixture
def sample_drift_events():
    """Load sample drift events from the demo corpus."""
    return json.loads(SAMPLE_DRIFT_PATH.read_text())


@pytest.fixture
def policy_pack_path():
    """Return the path to the demo policy pack."""
    return str(POLICY_PACK_PATH)


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
