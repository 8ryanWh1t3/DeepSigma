"""Tests for institutional_memory package and RE-F13→F19 handlers."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.institutional_memory.models import (
    ConsolidationReport,
    KnowledgeEntry,
    PatternFingerprint,
    Precedent,
    TemporalRecallResult,
)
from core.institutional_memory.registry import PrecedentRegistry
from core.institutional_memory.fingerprinting import compute_fingerprint, similarity_score
from core.institutional_memory.consolidation import merge_precedents
from core.institutional_memory.temporal import apply_decay, filter_by_window
from core.institutional_memory.validators import validate_precedent, validate_knowledge_entry


# ── Model Tests ──────────────────────────────────────────────────


class TestModels:
    def test_precedent_defaults(self):
        p = Precedent(
            precedent_id="PREC-001",
            source_session_id="RS-001",
            source_episode_ids=["EP-001"],
            takeaway="Always check drift before sealing",
            category="degrade_pattern",
        )
        assert p.confidence == 0.0
        assert p.relevance_score == 1.0
        assert p.decay_half_life_days == 90

    def test_knowledge_entry_defaults(self):
        ke = KnowledgeEntry(
            entry_id="KE-001",
            title="Drift patterns",
            summary="Multiple drift recurrence patterns observed",
        )
        assert ke.relevance_score == 1.0
        assert ke.access_count == 0


# ── Registry Tests ───────────────────────────────────────────────


class TestPrecedentRegistry:
    def test_add_and_get(self):
        reg = PrecedentRegistry()
        p = Precedent(
            precedent_id="PREC-001",
            source_session_id="RS-001",
            source_episode_ids=["EP-001"],
            takeaway="test",
            category="drift_recurrence",
        )
        reg.add(p)
        assert reg.get("PREC-001") is p
        assert reg.get("PREC-999") is None

    def test_list_by_category(self):
        reg = PrecedentRegistry()
        for i, cat in enumerate(["degrade_pattern", "drift_recurrence", "degrade_pattern"]):
            reg.add(Precedent(
                precedent_id=f"PREC-{i}",
                source_session_id="RS",
                source_episode_ids=[],
                takeaway=f"takeaway {i}",
                category=cat,
            ))
        assert len(reg.list_by_category("degrade_pattern")) == 2
        assert len(reg.list_by_category("drift_recurrence")) == 1

    def test_remove(self):
        reg = PrecedentRegistry()
        reg.add(Precedent(
            precedent_id="PREC-X",
            source_session_id="RS",
            source_episode_ids=[],
            takeaway="x",
            category="outcome_anomaly",
        ))
        assert reg.remove("PREC-X") is True
        assert reg.remove("PREC-X") is False

    def test_knowledge_entry_lifecycle(self):
        reg = PrecedentRegistry()
        ke = KnowledgeEntry(entry_id="KE-1", title="Test", summary="Summary")
        reg.add_knowledge_entry(ke)
        assert reg.get_knowledge_entry("KE-1") is ke
        assert len(reg.list_knowledge_entries()) == 1


# ── Fingerprinting Tests ────────────────────────────────────────


class TestFingerprinting:
    def test_compute_fingerprint_basic(self):
        episodes = [
            {"outcome_code": "success", "drift_signals": [{"driftType": "time"}]},
            {"outcome_code": "success", "drift_signals": []},
            {"outcome_code": "fail", "degrade_step": "yellow"},
        ]
        fp = compute_fingerprint("PREC-001", episodes)
        assert fp.precedent_id == "PREC-001"
        assert fp.episode_count == 3
        assert fp.outcome_vector["success"] == pytest.approx(2 / 3, abs=0.01)
        assert fp.drift_signature["time"] == 1
        assert fp.degrade_frequency == pytest.approx(1 / 3, abs=0.01)

    def test_compute_fingerprint_empty(self):
        fp = compute_fingerprint("PREC-X", [])
        assert fp.episode_count == 0
        assert fp.outcome_vector == {}

    def test_similarity_score_identical(self):
        fp = compute_fingerprint("A", [
            {"outcome_code": "success", "drift_signals": [{"driftType": "time"}]}
        ])
        score = similarity_score(fp, fp)
        assert score == 1.0

    def test_similarity_score_different(self):
        fp_a = compute_fingerprint("A", [
            {"outcome_code": "success", "drift_signals": [{"driftType": "time"}]}
        ])
        fp_b = compute_fingerprint("B", [
            {"outcome_code": "fail", "drift_signals": [{"driftType": "bypass"}]}
        ])
        score = similarity_score(fp_a, fp_b)
        assert score == 0.0


# ── Consolidation Tests ─────────────────────────────────────────


class TestConsolidation:
    def test_merge_precedents_groups_by_category(self):
        precedents = [
            Precedent(precedent_id=f"P-{i}", source_session_id="RS",
                      source_episode_ids=[], takeaway=f"take {i}",
                      category="degrade_pattern", relevance_score=0.9)
            for i in range(3)
        ]
        entries, report = merge_precedents(precedents, similarity_threshold=0.5)
        assert report.total_precedents == 3
        assert report.entries_created >= 1
        assert all(isinstance(e, KnowledgeEntry) for e in entries)

    def test_merge_single_precedent_no_merge(self):
        precedents = [
            Precedent(precedent_id="P-0", source_session_id="RS",
                      source_episode_ids=[], takeaway="solo",
                      category="degrade_pattern"),
        ]
        entries, report = merge_precedents(precedents)
        assert report.entries_created == 0


# ── Temporal Tests ───────────────────────────────────────────────


class TestTemporal:
    def test_apply_decay_reduces_relevance(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=90)  # One half-life
        p = Precedent(
            precedent_id="P-1", source_session_id="RS",
            source_episode_ids=[], takeaway="old learning",
            category="degrade_pattern", relevance_score=1.0,
            decay_half_life_days=90, created_at=old.isoformat(),
        )
        apply_decay([p], reference_time=now)
        assert p.relevance_score < 0.6  # Should be ~0.5 after one half-life

    def test_apply_decay_recent_stays_high(self):
        now = datetime.now(timezone.utc)
        p = Precedent(
            precedent_id="P-2", source_session_id="RS",
            source_episode_ids=[], takeaway="fresh",
            category="degrade_pattern", relevance_score=1.0,
            decay_half_life_days=90, created_at=now.isoformat(),
        )
        apply_decay([p], reference_time=now)
        assert p.relevance_score >= 0.99

    def test_filter_by_window(self):
        now = datetime.now(timezone.utc)
        precedents = [
            Precedent(
                precedent_id="P-recent", source_session_id="RS",
                source_episode_ids=[], takeaway="recent",
                category="degrade_pattern",
                created_at=(now - timedelta(hours=2)).isoformat(),
            ),
            Precedent(
                precedent_id="P-old", source_session_id="RS",
                source_episode_ids=[], takeaway="old",
                category="degrade_pattern",
                created_at=(now - timedelta(hours=48)).isoformat(),
            ),
        ]
        result = filter_by_window(precedents, window_hours=24, reference_time=now)
        assert result.total_matches == 1
        assert result.precedents[0].precedent_id == "P-recent"


# ── Validator Tests ──────────────────────────────────────────────


class TestValidators:
    def test_validate_precedent_valid(self):
        errors = validate_precedent({
            "takeaway": "Always check drift",
            "sourceSessionId": "RS-001",
            "category": "degrade_pattern",
            "confidence": 0.8,
        })
        assert errors == []

    def test_validate_precedent_missing_takeaway(self):
        errors = validate_precedent({"sourceSessionId": "RS-001", "confidence": 0.5})
        assert any("takeaway" in e for e in errors)

    def test_validate_precedent_invalid_category(self):
        errors = validate_precedent({
            "takeaway": "test", "sourceSessionId": "RS",
            "category": "invalid", "confidence": 0.5,
        })
        assert any("category" in e for e in errors)

    def test_validate_knowledge_entry_valid(self):
        errors = validate_knowledge_entry({"title": "Test", "summary": "Summary"})
        assert errors == []


# ── Handler Tests (RE-F13 through RE-F19) ────────────────────────


class TestReflectionOpsInstitutionalMemory:
    """Test the RE-F13→F19 handlers via ReflectionOps mode."""

    def _make_mode(self):
        from core.modes.reflectionops import ReflectionOps
        return ReflectionOps()

    def _ctx(self, **extras):
        from core.memory_graph import MemoryGraph
        ctx = {
            "memory_graph": MemoryGraph(),
            "now": datetime.now(timezone.utc),
            "precedent_registry": PrecedentRegistry(),
        }
        ctx.update(extras)
        return ctx

    def test_re_f13_precedent_ingest(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("RE-F13", {
            "payload": {
                "sessionId": "RS-001",
                "takeaways": ["Always verify before sealing", "Drift recurrence detected"],
                "episodeIds": ["EP-001", "EP-002"],
                "category": "degrade_pattern",
                "confidence": 0.7,
            }
        }, ctx)
        assert result.success
        assert len(result.mg_updates) == 2
        ev = result.events_emitted[0]
        assert ev["subtype"] == "precedent_stored"
        assert ev["count"] == 2

    def test_re_f14_pattern_fingerprint(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("RE-F14", {
            "payload": {
                "precedentId": "PREC-001",
                "episodes": [
                    {"outcome_code": "success", "drift_signals": [{"driftType": "time"}]},
                    {"outcome_code": "fail"},
                ],
            }
        }, ctx)
        assert result.success
        assert len(result.mg_updates) == 1
        ev = result.events_emitted[0]
        assert ev["subtype"] == "fingerprint_computed"
        assert ev["episodeCount"] == 2

    def test_re_f15_precedent_match(self):
        mode = self._make_mode()
        reg = PrecedentRegistry()
        reg.add(Precedent(
            precedent_id="P-1", source_session_id="RS",
            source_episode_ids=[], takeaway="test",
            category="degrade_pattern", relevance_score=0.8,
        ))
        ctx = self._ctx(precedent_registry=reg)
        result = mode.handle("RE-F15", {"payload": {"threshold": 0.5}}, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "precedent_matches"
        assert ev["count"] >= 1

    def test_re_f16_knowledge_consolidate(self):
        mode = self._make_mode()
        reg = PrecedentRegistry()
        for i in range(3):
            reg.add(Precedent(
                precedent_id=f"P-{i}", source_session_id="RS",
                source_episode_ids=[], takeaway=f"takeaway {i}",
                category="degrade_pattern", relevance_score=0.9,
            ))
        ctx = self._ctx(precedent_registry=reg)
        result = mode.handle("RE-F16", {"payload": {}}, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "knowledge_consolidated"

    def test_re_f17_temporal_recall(self):
        mode = self._make_mode()
        reg = PrecedentRegistry()
        reg.add(Precedent(
            precedent_id="P-recent", source_session_id="RS",
            source_episode_ids=[], takeaway="recent",
            category="degrade_pattern",
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        ctx = self._ctx(precedent_registry=reg)
        result = mode.handle("RE-F17", {"payload": {"windowHours": 24}}, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "temporal_recall_result"
        assert ev["totalMatches"] >= 1

    def test_re_f18_knowledge_decay(self):
        mode = self._make_mode()
        reg = PrecedentRegistry()
        old_time = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        reg.add(Precedent(
            precedent_id="P-old", source_session_id="RS",
            source_episode_ids=[], takeaway="old",
            category="degrade_pattern", relevance_score=1.0,
            decay_half_life_days=90, created_at=old_time,
        ))
        ctx = self._ctx(precedent_registry=reg)
        result = mode.handle("RE-F18", {"payload": {"demoteThreshold": 0.3}}, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "knowledge_decayed"
        # After 2 half-lives, score should be ~0.25
        p = reg.get("P-old")
        assert p.relevance_score < 0.3

    def test_re_f19_iris_precedent_resolve(self):
        mode = self._make_mode()
        reg = PrecedentRegistry()
        reg.add(Precedent(
            precedent_id="P-1", source_session_id="RS",
            source_episode_ids=[], takeaway="useful insight",
            category="drift_recurrence", relevance_score=0.9,
        ))
        ctx = self._ctx(precedent_registry=reg)
        result = mode.handle("RE-F19", {
            "payload": {"category": "drift_recurrence"}
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "iris_precedent_response"
        assert ev["status"] == "resolved"
        assert len(ev["results"]) == 1

    def test_all_handlers_registered(self):
        mode = self._make_mode()
        for fid in [f"RE-F{i}" for i in range(13, 20)]:
            assert mode.has_handler(fid), f"Handler {fid} not registered"
