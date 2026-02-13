"""Unit tests for coherence_ops.dlr — Decision Log Record builder."""
import json
import pytest
from coherence_ops.dlr import DLRBuilder, DLREntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_episode(**overrides):
    """Minimal sealed episode dict for testing."""
    base = {
        "episodeId": "ep-test-001",
        "decisionType": "AccountQuarantine",
        "dteRef": {
            "deadlineBudgetMs": 250,
            "ttlMs": 30000,
        },
        "actions": [
            {
                "type": "quarantine",
                "blastRadiusTier": "account",
                "idempotencyKey": "ik-001",
                "rollbackPlan": "unquarantine",
                "authorization": {"mode": "rbac"},
                "targetRefs": ["acc-001"],
            }
        ],
        "verification": {"result": "pass", "method": "read_after_write"},
        "policy": {
            "policyPackId": "demo_policy_pack_v1",
            "version": "1.0.0",
        },
        "outcome": {"code": "success"},
        "degrade": {"step": "none"},
        "sealedAt": "2026-02-12T12:00:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDLRBuilder:
    """DLRBuilder.from_episode produces valid DLREntry objects."""

    def test_single_episode(self):
        builder = DLRBuilder()
        ep = _make_episode()
        entry = builder.from_episode(ep)
        assert isinstance(entry, DLREntry)
        assert entry.episode_id == "ep-test-001"
        assert entry.decision_type == "AccountQuarantine"
        assert entry.dlr_id.startswith("dlr-")
        assert entry.outcome_code == "success"

    def test_dlr_id_deterministic(self):
        b1 = DLRBuilder()
        b2 = DLRBuilder()
        id1 = b1.from_episode(_make_episode()).dlr_id
        id2 = b2.from_episode(_make_episode()).dlr_id
        assert id1 == id2, "Same episode should yield same dlr_id"

    def test_dte_ref_preserved(self):
        builder = DLRBuilder()
        entry = builder.from_episode(_make_episode())
        assert entry.dte_ref["deadlineBudgetMs"] == 250

    def test_action_contract_extracted(self):
        builder = DLRBuilder()
        entry = builder.from_episode(_make_episode())
        assert entry.action_contract is not None
        assert entry.action_contract["blastRadiusTier"] == "account"
        assert entry.action_contract["idempotencyKey"] == "ik-001"
        assert entry.action_contract["authMode"] == "rbac"

    def test_no_actions_yields_none(self):
        builder = DLRBuilder()
        entry = builder.from_episode(_make_episode(actions=[]))
        assert entry.action_contract is None

    def test_verification_stored(self):
        builder = DLRBuilder()
        entry = builder.from_episode(_make_episode())
        assert entry.verification["result"] == "pass"

    def test_policy_stamp_stored(self):
        builder = DLRBuilder()
        entry = builder.from_episode(_make_episode())
        assert entry.policy_stamp["policyPackId"] == "demo_policy_pack_v1"

    def test_degrade_step(self):
        builder = DLRBuilder()
        entry = builder.from_episode(
            _make_episode(degrade={"step": "fallback_cache"})
        )
        assert entry.degrade_step == "fallback_cache"

    def test_batch_from_episodes(self):
        builder = DLRBuilder()
        eps = [
            _make_episode(episodeId="ep-1"),
            _make_episode(episodeId="ep-2"),
            _make_episode(episodeId="ep-3"),
        ]
        entries = builder.from_episodes(eps)
        assert len(entries) == 3
        assert builder.entries == entries

    def test_to_json_roundtrip(self):
        builder = DLRBuilder()
        builder.from_episode(_make_episode())
        raw = builder.to_json()
        data = json.loads(raw)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["episode_id"] == "ep-test-001"

    def test_clear(self):
        builder = DLRBuilder()
        builder.from_episode(_make_episode())
        assert len(builder.entries) == 1
        builder.clear()
        assert len(builder.entries) == 0

    def test_to_dict_list(self):
        builder = DLRBuilder()
        builder.from_episode(_make_episode())
        dicts = builder.to_dict_list()
        assert isinstance(dicts, list)
        assert "dlr_id" in dicts[0]
