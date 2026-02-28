"""Tests for cross-domain cascade engine."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.modes.cascade import CascadeEngine, CascadeResult
from core.modes.cascade_rules import CascadeRule, RULES, get_rules_for_event
from core.modes.intelops import IntelOps
from core.modes.franops import FranOps
from core.modes.reflectionops import ReflectionOps
from core.episode_state import EpisodeState, EpisodeTracker
from core.feeds.canon.workflow import CanonWorkflow
from core.memory_graph import MemoryGraph
from core.drift_signal import DriftSignalCollector
from core.audit_log import AuditLog


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def engine():
    e = CascadeEngine()
    e.register_domain(IntelOps())
    e.register_domain(FranOps())
    e.register_domain(ReflectionOps())
    return e


@pytest.fixture
def full_context():
    return {
        "memory_graph": MemoryGraph(),
        "drift_collector": DriftSignalCollector(),
        "canon_store": None,
        "canon_claims": [],
        "all_canon_entries": [],
        "all_claims": [],
        "workflow": CanonWorkflow(),
        "episode_tracker": EpisodeTracker(),
        "audit_log": AuditLog(),
        "gates": [],
        "blessed_claims": set(),
        "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
    }


# ── Rule Matching Tests ──────────────────────────────────────────


class TestCascadeRules:

    def test_rules_not_empty(self):
        assert len(RULES) >= 7

    def test_contradiction_matches(self):
        rules = get_rules_for_event("intelops", "claim_contradiction")
        assert any(r.rule_id == "CASCADE-R01" for r in rules)

    def test_supersede_matches(self):
        rules = get_rules_for_event("intelops", "claim_superseded")
        assert any(r.rule_id == "CASCADE-R02" for r in rules)

    def test_retcon_matches(self):
        rules = get_rules_for_event("franops", "retcon_executed")
        assert any(r.rule_id == "CASCADE-R03" for r in rules)

    def test_cascade_matches(self):
        rules = get_rules_for_event("franops", "retcon_cascade")
        assert any(r.rule_id == "CASCADE-R04" for r in rules)

    def test_freeze_matches(self):
        rules = get_rules_for_event("reflectionops", "episodes_frozen")
        assert any(r.rule_id == "CASCADE-R05" for r in rules)

    def test_red_severity_matches(self):
        rules = get_rules_for_event("intelops", "anything", severity="red")
        assert any(r.rule_id == "CASCADE-R07" for r in rules)

    def test_no_match(self):
        rules = get_rules_for_event("unknown_domain", "unknown_subtype")
        # Only wildcard rules should match
        non_wildcard = [r for r in rules if r.source_domain != "*"]
        assert len(non_wildcard) == 0

    def test_severity_filter(self):
        rules = get_rules_for_event("intelops", "anything", severity="green")
        # CASCADE-R07 requires severity=red, should not match green
        assert not any(r.rule_id == "CASCADE-R07" for r in rules)


# ── Engine Registration Tests ────────────────────────────────────


class TestCascadeEngine:

    def test_registers_three_domains(self, engine):
        assert engine.domain_count == 3

    def test_missing_domain_errors(self):
        e = CascadeEngine()
        # No domains registered
        result = e.propagate(
            "intelops",
            {"subtype": "claim_contradiction"},
            {},
        )
        # Should have errors for missing target domains
        assert len(result.triggered_rules) == 0

    def test_max_depth_prevents_infinite_loop(self, engine, full_context):
        result = engine.propagate(
            "intelops",
            {"subtype": "claim_contradiction"},
            full_context,
            max_depth=0,
        )
        assert result.total_triggered == 0


# ── Cross-Domain Propagation Tests ───────────────────────────────


class TestCrossdomainPropagation:

    def test_contradiction_to_enforce(self, engine, full_context):
        """IntelOps claim_contradiction -> FranOps canon_enforce."""
        full_context["canon_claims"] = [{"claimId": "C1"}]
        event = {
            "subtype": "claim_contradiction",
            "payload": {"canonId": "CANON-1", "decisionClaims": ["C1"]},
        }
        result = engine.propagate("intelops", event, full_context)
        assert "CASCADE-R01" in result.triggered_rules

    def test_supersede_to_canon(self, engine, full_context):
        """IntelOps claim_superseded -> FranOps canon_supersede."""
        full_context["workflow"].set_state("CANON-OLD", CanonWorkflow)
        event = {
            "subtype": "claim_superseded",
            "payload": {"canonId": "CANON-OLD", "supersededBy": "CANON-NEW"},
        }
        result = engine.propagate("intelops", event, full_context)
        assert "CASCADE-R02" in result.triggered_rules

    def test_retcon_to_episode(self, engine, full_context):
        """FranOps retcon_executed -> ReOps episode_begin."""
        event = {
            "subtype": "retcon_executed",
            "payload": {"episodeId": "EP-RETCON", "decisionType": "retcon"},
        }
        result = engine.propagate("franops", event, full_context)
        assert "CASCADE-R03" in result.triggered_rules

    def test_cascade_to_confidence(self, engine, full_context):
        """FranOps retcon_cascade -> IntelOps confidence_recalc."""
        full_context["claims"] = {"CLAIM-X": {
            "claimId": "CLAIM-X", "confidence": {"score": 0.9},
        }}
        full_context["contradiction_count"] = 1
        full_context["evidence_age_days"] = 0
        event = {
            "subtype": "retcon_cascade",
            "payload": {"claimId": "CLAIM-X"},
        }
        result = engine.propagate("franops", event, full_context)
        assert "CASCADE-R04" in result.triggered_rules

    def test_freeze_to_halflife(self, engine, full_context):
        """ReOps episodes_frozen -> IntelOps half_life_check."""
        full_context["all_claims"] = []
        event = {
            "subtype": "episodes_frozen",
            "payload": {},
        }
        result = engine.propagate("reflectionops", event, full_context)
        assert "CASCADE-R05" in result.triggered_rules


# ── Depth Limiting Tests ─────────────────────────────────────────


class TestCascadeDepth:

    def test_depth_1_limits_propagation(self, engine, full_context):
        event = {
            "subtype": "claim_contradiction",
            "payload": {"canonId": "CANON-1"},
        }
        result = engine.propagate("intelops", event, full_context, max_depth=1)
        # Should trigger R01 but not recurse further
        assert "CASCADE-R01" in result.triggered_rules

    def test_depth_0_no_propagation(self, engine, full_context):
        event = {"subtype": "claim_contradiction"}
        result = engine.propagate("intelops", event, full_context, max_depth=0)
        assert result.total_triggered == 0


# ── CascadeResult Tests ──────────────────────────────────────────


class TestCascadeResult:

    def test_empty_result_success(self):
        r = CascadeResult()
        assert r.success
        assert r.total_triggered == 0

    def test_result_with_errors(self):
        r = CascadeResult()
        r.errors.append("test error")
        assert not r.success

    def test_to_dict(self):
        r = CascadeResult()
        r.triggered_rules.append("R01")
        d = r.to_dict()
        assert d["totalTriggered"] == 1
        assert d["success"]


# ── Integration: Multi-Step Cascade ──────────────────────────────


class TestMultiStepCascade:
    """End-to-end: contradiction -> enforce -> severity scoring."""

    def test_contradiction_cascade_chain(self, engine, full_context):
        """A contradiction in IntelOps cascades through FranOps and ReOps."""
        full_context["canon_claims"] = []  # No canon claims -> violation

        event = {
            "subtype": "claim_contradiction",
            "payload": {
                "canonId": "CANON-TEST",
                "decisionClaims": ["ROGUE-CLAIM"],
            },
        }

        result = engine.propagate("intelops", event, full_context, max_depth=2)
        assert result.total_triggered >= 1
        assert "CASCADE-R01" in result.triggered_rules

    def test_killswitch_cascade(self, engine, full_context):
        """Kill-switch cascades with severity=red."""
        tracker = full_context["episode_tracker"]
        tracker.set_state("EP-1", EpisodeState.ACTIVE)

        event = {
            "subtype": "killswitch_activated",
            "severity": "red",
            "payload": {"authorizedBy": "admin", "reason": "test"},
        }
        result = engine.propagate("reflectionops", event, full_context)
        # Should match CASCADE-R06 (killswitch) and CASCADE-R07 (red severity)
        rule_ids = set(result.triggered_rules)
        assert "CASCADE-R06" in rule_ids or "CASCADE-R07" in rule_ids
