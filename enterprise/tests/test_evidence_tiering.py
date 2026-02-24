"""Tests for credibility_engine/tiering.py — hot/warm/cold evidence tiering.

Run:  pytest tests/test_evidence_tiering.py -v
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from credibility_engine.store import CredibilityStore
from credibility_engine.tiering import (
    EvidenceTier,
    EvidenceTierManager,
    TieringPolicy,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ago(minutes: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return dt.isoformat().replace("+00:00", "Z")


def _make_claim(claim_id: str, age_minutes: int = 0, ttl_remaining: int = 240) -> dict:
    return {
        "id": claim_id,
        "title": f"Claim {claim_id}",
        "state": "VERIFIED",
        "ttl_remaining": ttl_remaining,
        "timestamp": _ago(age_minutes),
        "last_verified": _ago(age_minutes),
    }


def _make_drift(drift_id: str, age_minutes: int = 0, severity: str = "low") -> dict:
    return {
        "id": drift_id,
        "severity": severity,
        "timestamp": _ago(age_minutes),
    }


@pytest.fixture
def store(tmp_path):
    return CredibilityStore(data_dir=tmp_path)


@pytest.fixture
def manager(store):
    return EvidenceTierManager(store)


# ── EvidenceTier ─────────────────────────────────────────────────────────────

class TestEvidenceTier:
    def test_enum_values(self):
        assert EvidenceTier.HOT.value == "hot"
        assert EvidenceTier.WARM.value == "warm"
        assert EvidenceTier.COLD.value == "cold"

    def test_ordering(self):
        assert EvidenceTier.HOT < EvidenceTier.WARM
        assert EvidenceTier.WARM < EvidenceTier.COLD
        assert not EvidenceTier.COLD < EvidenceTier.HOT


# ── TieringPolicy ───────────────────────────────────────────────────────────

class TestTieringPolicy:
    def test_defaults(self):
        policy = TieringPolicy()
        assert policy.hot_max_age_minutes == 1440
        assert policy.warm_max_age_minutes == 43200
        assert policy.ttl_expiry_demotes is True
        assert policy.cold_excludes_scoring is True

    def test_custom_values(self):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        assert policy.hot_max_age_minutes == 60
        assert policy.warm_max_age_minutes == 120

    def test_to_dict(self):
        policy = TieringPolicy()
        d = policy.to_dict()
        assert "hot_max_age_minutes" in d
        assert "warm_max_age_minutes" in d
        assert "ttl_expiry_demotes" in d
        assert "cold_excludes_scoring" in d


# ── Classification ───────────────────────────────────────────────────────────

class TestClassification:
    def test_fresh_claim_is_hot(self, manager):
        record = _make_claim("C-001", age_minutes=10, ttl_remaining=200)
        assert manager.classify(record) == EvidenceTier.HOT

    def test_25h_old_claim_is_warm(self, manager):
        record = _make_claim("C-002", age_minutes=25 * 60, ttl_remaining=200)
        assert manager.classify(record) == EvidenceTier.WARM

    def test_31_day_old_claim_is_cold(self, manager):
        record = _make_claim("C-003", age_minutes=31 * 24 * 60, ttl_remaining=200)
        assert manager.classify(record) == EvidenceTier.COLD

    def test_expired_ttl_demotes_to_warm(self, manager):
        record = _make_claim("C-004", age_minutes=10, ttl_remaining=0)
        assert manager.classify(record) == EvidenceTier.WARM

    def test_expired_ttl_stays_hot_when_demotion_disabled(self, store):
        policy = TieringPolicy(ttl_expiry_demotes=False)
        mgr = EvidenceTierManager(store, policy)
        record = _make_claim("C-005", age_minutes=10, ttl_remaining=0)
        assert mgr.classify(record) == EvidenceTier.HOT

    def test_missing_timestamp_defaults_to_hot(self, manager):
        record = {"id": "C-006", "title": "No timestamp"}
        assert manager.classify(record) == EvidenceTier.HOT

    def test_negative_ttl_demotes(self, manager):
        record = _make_claim("C-007", age_minutes=10, ttl_remaining=-50)
        assert manager.classify(record) == EvidenceTier.WARM


# ── Sweep ────────────────────────────────────────────────────────────────────

class TestSweep:
    def test_sweep_with_mixed_age_records(self, store):
        # Use small thresholds for testability
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        # Write mixed-age claims to the primary file
        claims = [
            _make_claim("C-hot", age_minutes=10),       # 10min → hot
            _make_claim("C-warm", age_minutes=90),       # 90min → warm
            _make_claim("C-cold", age_minutes=200),      # 200min → cold
        ]
        store.save_claims(claims)

        result = mgr.sweep()
        assert result.by_tier["hot"] >= 1
        assert result.by_tier["warm"] >= 1
        assert result.by_tier["cold"] >= 1

        # Verify tier files exist with correct content
        hot_claims = store.load_all(CredibilityStore.CLAIMS_FILE)
        warm_claims = store.load_warm(CredibilityStore.CLAIMS_FILE)
        cold_claims = store.load_cold(CredibilityStore.CLAIMS_FILE)

        assert len(hot_claims) == 1
        assert len(warm_claims) == 1
        assert len(cold_claims) == 1

    def test_sweep_preserves_all_records(self, store):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        claims = [_make_claim(f"C-{i}", age_minutes=i * 50) for i in range(5)]
        store.save_claims(claims)

        mgr.sweep()

        # All records should still exist across tiers
        all_records = mgr._load_all_tiers(CredibilityStore.CLAIMS_FILE)
        assert len(all_records) == 5

    def test_empty_store_noop(self, manager):
        result = manager.sweep()
        assert result.files_processed == 0
        assert result.by_tier == {"hot": 0, "warm": 0, "cold": 0}

    def test_sweep_idempotent(self, store):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        claims = [
            _make_claim("C-hot", age_minutes=10),
            _make_claim("C-warm", age_minutes=90),
        ]
        store.save_claims(claims)

        now = datetime.now(timezone.utc)
        result1 = mgr.sweep(now=now)
        result2 = mgr.sweep(now=now)
        assert result1.by_tier == result2.by_tier

    def test_sweep_counts_accurate(self, store):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        claims = [
            _make_claim("C-1", age_minutes=10),
            _make_claim("C-2", age_minutes=20),
            _make_claim("C-3", age_minutes=90),
        ]
        store.save_claims(claims)
        result = mgr.sweep()
        total = result.by_tier["hot"] + result.by_tier["warm"] + result.by_tier["cold"]
        assert total == 3


# ── Tier-Aware Queries ───────────────────────────────────────────────────────

class TestTierAwareQueries:
    def _setup_tiered_data(self, store):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        claims = [
            _make_claim("C-hot-1", age_minutes=10),
            _make_claim("C-hot-2", age_minutes=20),
            _make_claim("C-warm-1", age_minutes=90),
            _make_claim("C-cold-1", age_minutes=200),
        ]
        store.save_claims(claims)
        mgr.sweep()
        return mgr

    def test_get_claims_hot_only(self, store):
        mgr = self._setup_tiered_data(store)
        hot = mgr.get_claims(EvidenceTier.HOT)
        assert len(hot) == 2

    def test_get_claims_warm_includes_hot(self, store):
        mgr = self._setup_tiered_data(store)
        warm = mgr.get_claims(EvidenceTier.WARM)
        assert len(warm) == 3  # 2 hot + 1 warm

    def test_get_scoring_claims_excludes_cold(self, store):
        mgr = self._setup_tiered_data(store)
        scoring = mgr.get_scoring_claims()
        assert len(scoring) == 3  # hot + warm, no cold

    def test_get_scoring_drift_capped(self, store):
        policy = TieringPolicy(hot_max_age_minutes=60, warm_max_age_minutes=120)
        mgr = EvidenceTierManager(store, policy)

        # Write more than 500 drift events
        drifts = [_make_drift(f"D-{i}", age_minutes=10) for i in range(10)]
        for d in drifts:
            store.append_drift(d)

        result = mgr.get_scoring_drift(n=5)
        assert len(result) == 5

    def test_tier_summary_correct_counts(self, store):
        mgr = self._setup_tiered_data(store)
        summary = mgr.tier_summary()
        assert "claims" in summary["tiers"]
        claims_tiers = summary["tiers"]["claims"]
        assert claims_tiers["hot"] == 2
        assert claims_tiers["warm"] == 1
        assert claims_tiers["cold"] == 1
        assert claims_tiers["total"] == 4


# ── Engine Integration ───────────────────────────────────────────────────────

_has_fastapi = True
try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    _has_fastapi = False


@pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
class TestEngineIntegration:
    def test_engine_with_tiering_uses_hot_warm(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        engine.initialize_default_state()

        # Enable tiering
        engine.enable_tiering()
        assert engine.tier_manager is not None

        # Recalculate should work
        result = engine.recalculate_index()
        assert "score" in result
        assert "band" in result

    def test_engine_without_tiering_backward_compatible(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        engine.initialize_default_state()

        # No tiering enabled
        assert engine.tier_manager is None
        result = engine.recalculate_index()
        assert "score" in result

    def test_run_tier_sweep(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        engine.initialize_default_state()
        engine.enable_tiering()

        result = engine.run_tier_sweep()
        assert "by_tier" in result
        assert "promoted" in result
        assert "demoted" in result

    def test_run_tier_sweep_without_tiering_raises(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        with pytest.raises(RuntimeError, match="Tiering is not enabled"):
            engine.run_tier_sweep()

    def test_snapshot_includes_tiering_data(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        engine.initialize_default_state()
        engine.enable_tiering()

        snap = engine.snapshot_credibility()
        assert "tiering" in snap
        assert snap["tiering"] is not None
        assert "tiers" in snap["tiering"]
        assert "policy" in snap["tiering"]

    def test_snapshot_without_tiering_has_null(self, tmp_path):
        from credibility_engine.engine import CredibilityEngine

        store = CredibilityStore(data_dir=tmp_path)
        engine = CredibilityEngine(store=store)
        engine.initialize_default_state()

        snap = engine.snapshot_credibility()
        assert snap["tiering"] is None


# ── Store Tier Helpers ───────────────────────────────────────────────────────

class TestStoreTierHelpers:
    def test_load_warm_empty(self, store):
        assert store.load_warm("claims.jsonl") == []

    def test_load_cold_empty(self, store):
        assert store.load_cold("claims.jsonl") == []

    def test_write_and_load_warm(self, store):
        records = [{"id": "W-1", "state": "VERIFIED"}]
        store.write_warm("claims.jsonl", records)
        loaded = store.load_warm("claims.jsonl")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "W-1"

    def test_write_and_load_cold(self, store):
        records = [{"id": "C-1", "state": "VERIFIED"}]
        store.write_cold("claims.jsonl", records)
        loaded = store.load_cold("claims.jsonl")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "C-1"

    def test_write_empty_removes_file(self, store):
        records = [{"id": "W-1"}]
        store.write_warm("claims.jsonl", records)
        assert store._tier_path("claims.jsonl", "warm").exists()
        store.write_warm("claims.jsonl", [])
        assert not store._tier_path("claims.jsonl", "warm").exists()

    def test_tier_path_naming(self, store):
        path = store._tier_path("claims.jsonl", "warm")
        assert path.name == "claims-warm.jsonl"
        path = store._tier_path("drift.jsonl", "cold")
        assert path.name == "drift-cold.jsonl"
