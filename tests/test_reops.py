"""Tests for ReflectionOps domain mode — 12 function handlers."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.modes.base import DomainMode, FunctionResult
from core.modes.reflectionops import ReflectionOps
from core.episode_state import EpisodeState, EpisodeTracker
from core.severity import (
    aggregate_severity,
    classify_severity,
    compute_severity_score,
)
from core.audit_log import AuditEntry, AuditLog
from core.killswitch import activate_killswitch
from core.memory_graph import MemoryGraph
from core.drift_signal import DriftSignalCollector


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def reops() -> ReflectionOps:
    return ReflectionOps()


@pytest.fixture
def tracker() -> EpisodeTracker:
    return EpisodeTracker()


@pytest.fixture
def audit_log() -> AuditLog:
    return AuditLog()


@pytest.fixture
def mg() -> MemoryGraph:
    return MemoryGraph()


@pytest.fixture
def ds() -> DriftSignalCollector:
    return DriftSignalCollector()


@pytest.fixture
def base_context(tracker, audit_log, mg, ds):
    return {
        "episode_tracker": tracker,
        "audit_log": audit_log,
        "memory_graph": mg,
        "drift_collector": ds,
        "gates": [],
        "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
    }


# ── Registration Tests ───────────────────────────────────────────


class TestReflectionOpsRegistration:

    def test_domain_name(self, reops):
        assert reops.domain == "reflectionops"

    def test_all_12_handlers_registered(self, reops):
        assert len(reops.function_ids) == 12

    def test_function_ids_well_formed(self, reops):
        for fid in reops.function_ids:
            assert fid.startswith("RE-F")

    def test_has_handler(self, reops):
        assert reops.has_handler("RE-F01")
        assert not reops.has_handler("FRAN-F01")

    def test_unknown_handler_returns_error(self, reops, base_context):
        result = reops.handle("NONEXISTENT-F99", {}, base_context)
        assert not result.success
        assert "No handler" in result.error


# ── RE-F01: Episode Begin ────────────────────────────────────────


class TestEpisodeBegin:

    def test_basic_begin(self, reops, base_context):
        event = {"payload": {"episodeId": "EP-001", "decisionType": "ingest"}}
        result = reops.handle("RE-F01", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "episode_active"

    def test_begin_sets_active(self, reops, base_context, tracker):
        event = {"payload": {"episodeId": "EP-002", "decisionType": "ingest"}}
        reops.handle("RE-F01", event, base_context)
        assert tracker.get_state("EP-002") == EpisodeState.ACTIVE

    def test_begin_adds_mg_node(self, reops, base_context, mg):
        event = {"payload": {"episodeId": "EP-003", "decisionType": "test"}}
        result = reops.handle("RE-F01", event, base_context)
        assert len(result.mg_updates) > 0


# ── RE-F02: Episode Seal ─────────────────────────────────────────


class TestEpisodeSeal:

    def test_seal_active_episode(self, reops, base_context, tracker):
        tracker.set_state("EP-001", EpisodeState.ACTIVE)
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F02", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "episode_sealed"
        assert "sealHash" in result.events_emitted[0]
        assert tracker.get_state("EP-001") == EpisodeState.SEALED

    def test_seal_wrong_state_emits_drift(self, reops, base_context, tracker):
        tracker.set_state("EP-001", EpisodeState.SEALED)
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F02", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0

    def test_seal_logs_audit(self, reops, base_context, tracker, audit_log):
        tracker.set_state("EP-001", EpisodeState.ACTIVE)
        event = {"payload": {"episodeId": "EP-001"}}
        reops.handle("RE-F02", event, base_context)
        assert audit_log.entry_count > 0


# ── RE-F03: Episode Archive ──────────────────────────────────────


class TestEpisodeArchive:

    def test_archive_sealed_episode(self, reops, base_context, tracker):
        tracker.set_state("EP-001", EpisodeState.SEALED)
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F03", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "episode_archived"
        assert tracker.get_state("EP-001") == EpisodeState.ARCHIVED

    def test_archive_wrong_state_emits_drift(self, reops, base_context, tracker):
        tracker.set_state("EP-001", EpisodeState.ACTIVE)
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F03", event, base_context)
        assert len(result.drift_signals) > 0


# ── RE-F04: Gate Evaluate ────────────────────────────────────────


class TestGateEvaluate:

    def test_gate_pass(self, reops, base_context):
        base_context["gates"] = [{"type": "latency", "threshold": 1000}]
        event = {"payload": {"episodeId": "EP-001", "gateContext": {"latency": 500}}}
        result = reops.handle("RE-F04", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "gate_pass"

    def test_gate_deny(self, reops, base_context):
        base_context["gates"] = [{"type": "latency", "threshold": 100}]
        event = {"payload": {"episodeId": "EP-001", "gateContext": {"latency": 500}}}
        result = reops.handle("RE-F04", event, base_context)
        assert result.events_emitted[0]["subtype"] == "gate_deny"
        assert len(result.drift_signals) > 0

    def test_gate_logs_audit(self, reops, base_context, audit_log):
        event = {"payload": {"episodeId": "EP-001", "gateContext": {}}}
        reops.handle("RE-F04", event, base_context)
        assert audit_log.entry_count > 0


# ── RE-F05: Gate Degrade ─────────────────────────────────────────


class TestGateDegrade:

    def test_degrade_applied(self, reops, base_context):
        event = {"payload": {"episodeId": "EP-001", "degradeStep": "cache_bundle"}}
        result = reops.handle("RE-F05", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "degrade_applied"
        assert result.events_emitted[0]["degradeStep"] == "cache_bundle"

    def test_degrade_logs_audit(self, reops, base_context, audit_log):
        event = {"payload": {"episodeId": "EP-001", "degradeStep": "rules_only"}}
        reops.handle("RE-F05", event, base_context)
        assert audit_log.entry_count > 0


# ── RE-F06: Gate Kill-Switch ─────────────────────────────────────


class TestGateKillswitch:

    def test_killswitch_freezes_episodes(self, reops, base_context, tracker):
        tracker.set_state("EP-A", EpisodeState.ACTIVE)
        tracker.set_state("EP-B", EpisodeState.ACTIVE)
        tracker.set_state("EP-C", EpisodeState.SEALED)  # should NOT be frozen
        event = {"payload": {"authorizedBy": "admin", "reason": "test"}}
        result = reops.handle("RE-F06", event, base_context)
        assert result.success
        assert tracker.get_state("EP-A") == EpisodeState.FROZEN
        assert tracker.get_state("EP-B") == EpisodeState.FROZEN
        assert tracker.get_state("EP-C") == EpisodeState.SEALED

    def test_killswitch_emits_halt_proof(self, reops, base_context, tracker):
        tracker.set_state("EP-A", EpisodeState.ACTIVE)
        event = {"payload": {"authorizedBy": "admin", "reason": "test"}}
        result = reops.handle("RE-F06", event, base_context)
        ks_event = result.events_emitted[0]
        assert ks_event["subtype"] == "killswitch_activated"
        assert ks_event["severity"] == "red"
        assert "sealHash" in ks_event

    def test_killswitch_logs_audit(self, reops, base_context, tracker, audit_log):
        tracker.set_state("EP-A", EpisodeState.ACTIVE)
        event = {"payload": {"authorizedBy": "admin", "reason": "test"}}
        reops.handle("RE-F06", event, base_context)
        assert audit_log.entry_count > 0


# ── RE-F07: Audit Non-Coercion ───────────────────────────────────


class TestAuditNonCoercion:

    def test_attestation_logged(self, reops, base_context, audit_log):
        event = {"payload": {"episodeId": "EP-001", "actor": "agent"}}
        result = reops.handle("RE-F07", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "non_coercion_attested"
        assert audit_log.entry_count > 0
        assert result.events_emitted[0]["chainHash"].startswith("sha256:")


# ── RE-F08: Severity Score ───────────────────────────────────────


class TestSeverityScore:

    def test_high_severity(self, reops, base_context):
        event = {"payload": {"driftType": "authority_mismatch", "severity": "red"}}
        result = reops.handle("RE-F08", event, base_context)
        assert result.success
        assert result.events_emitted[0]["computedScore"] > 0.7

    def test_low_severity(self, reops, base_context):
        event = {"payload": {"driftType": "time", "severity": "green"}}
        result = reops.handle("RE-F08", event, base_context)
        assert result.events_emitted[0]["computedScore"] < 0.3


# ── RE-F09: Coherence Check ──────────────────────────────────────


class TestCoherenceCheck:

    def test_green_coherence(self, reops, base_context):
        base_context["coherence_score"] = 90.0
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F09", event, base_context)
        assert result.events_emitted[0]["subtype"] == "coherence_green"
        assert len(result.drift_signals) == 0

    def test_red_coherence(self, reops, base_context):
        base_context["coherence_score"] = 30.0
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F09", event, base_context)
        assert result.events_emitted[0]["subtype"] == "coherence_red"
        assert len(result.drift_signals) > 0


# ── RE-F10: Reflection Ingest ────────────────────────────────────


class TestReflectionIngest:

    def test_ingest(self, reops, base_context):
        event = {"payload": {"episodeId": "EP-001"}}
        result = reops.handle("RE-F10", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "reflection_ingested"


# ── RE-F11: IRIS Resolve ─────────────────────────────────────────


class TestIRISResolve:

    def test_resolve_without_engine(self, reops, base_context):
        event = {"payload": {"queryType": "STATUS", "text": "what is the status?"}}
        result = reops.handle("RE-F11", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "iris_response"
        assert "queryId" in result.events_emitted[0]


# ── RE-F12: Episode Replay ──────────────────────────────────────


class TestEpisodeReplay:

    def test_replay_match(self, reops, base_context):
        replay_data = {"outcome": "success"}
        canonical = json.dumps(
            {"episodeId": "EP-001", **replay_data},
            sort_keys=True, separators=(",", ":"),
        )
        expected = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

        event = {"payload": {
            "episodeId": "EP-001",
            "expectedHash": expected,
            "replayData": replay_data,
        }}
        result = reops.handle("RE-F12", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "replay_pass"
        assert result.events_emitted[0]["matched"]

    def test_replay_mismatch(self, reops, base_context):
        event = {"payload": {
            "episodeId": "EP-001",
            "expectedHash": "sha256:wrong",
            "replayData": {"outcome": "success"},
        }}
        result = reops.handle("RE-F12", event, base_context)
        assert result.events_emitted[0]["subtype"] == "replay_fail"
        assert len(result.drift_signals) > 0

    def test_replay_logs_audit(self, reops, base_context, audit_log):
        event = {"payload": {
            "episodeId": "EP-001",
            "expectedHash": "sha256:x",
            "replayData": {},
        }}
        reops.handle("RE-F12", event, base_context)
        assert audit_log.entry_count > 0


# ── Support Module Tests ─────────────────────────────────────────


class TestEpisodeTracker:

    def test_transition_valid(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.PENDING)
        assert t.transition("EP-1", EpisodeState.ACTIVE)

    def test_transition_invalid(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.PENDING)
        assert not t.transition("EP-1", EpisodeState.SEALED)

    def test_freeze_all(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.ACTIVE)
        t.set_state("EP-2", EpisodeState.SEALED)
        frozen = t.freeze_all()
        assert "EP-1" in frozen
        assert "EP-2" not in frozen

    def test_active_episodes(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.ACTIVE)
        t.set_state("EP-2", EpisodeState.SEALED)
        assert t.active_episodes() == ["EP-1"]


class TestAuditLogModule:

    def test_append_and_chain(self):
        log = AuditLog()
        h1 = log.append(AuditEntry(entry_type="test1"))
        h2 = log.append(AuditEntry(entry_type="test2"))
        assert h1.startswith("sha256:")
        assert h2.startswith("sha256:")
        assert h1 != h2

    def test_verify_chain(self):
        log = AuditLog()
        log.append(AuditEntry(entry_type="a"))
        log.append(AuditEntry(entry_type="b"))
        log.append(AuditEntry(entry_type="c"))
        assert log.verify_chain()

    def test_entry_count(self):
        log = AuditLog()
        log.append(AuditEntry(entry_type="x"))
        assert log.entry_count == 1


class TestSeverityModule:

    def test_high_severity_score(self):
        score = compute_severity_score("authority_mismatch", "red")
        assert score >= 0.8

    def test_low_severity_score(self):
        score = compute_severity_score("time", "green")
        assert score < 0.2

    def test_classify_red(self):
        assert classify_severity(0.9) == "red"

    def test_classify_green(self):
        assert classify_severity(0.1) == "green"

    def test_aggregate_empty(self):
        result = aggregate_severity([])
        assert result["overall"] == "green"

    def test_aggregate_mixed(self):
        signals = [
            {"driftType": "authority_mismatch", "severity": "red"},
            {"driftType": "time", "severity": "green"},
        ]
        result = aggregate_severity(signals)
        assert result["overall"] == "red"


class TestKillswitchModule:

    def test_activate(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.ACTIVE)
        t.set_state("EP-2", EpisodeState.ACTIVE)
        proof = activate_killswitch(t, "admin", "test")
        assert proof["frozenCount"] == 2
        assert "sealHash" in proof

    def test_activate_with_audit(self):
        t = EpisodeTracker()
        t.set_state("EP-1", EpisodeState.ACTIVE)
        log = AuditLog()
        activate_killswitch(t, "admin", "test", audit_log=log)
        assert log.entry_count == 1


# ── Integration: Full Episode Lifecycle ──────────────────────────


class TestEpisodeLifecycle:
    """End-to-end: begin -> gate -> degrade -> seal -> archive."""

    def test_full_lifecycle(self, reops):
        t = EpisodeTracker()
        mg = MemoryGraph()
        log = AuditLog()
        ctx = {
            "episode_tracker": t,
            "audit_log": log,
            "memory_graph": mg,
            "drift_collector": DriftSignalCollector(),
            "gates": [],
            "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
        }

        # Step 1: Begin
        r1 = reops.handle("RE-F01", {"payload": {
            "episodeId": "EP-LC", "decisionType": "ingest",
        }}, ctx)
        assert r1.success
        assert t.get_state("EP-LC") == EpisodeState.ACTIVE

        # Step 2: Gate evaluate (pass)
        r2 = reops.handle("RE-F04", {"payload": {
            "episodeId": "EP-LC", "gateContext": {},
        }}, ctx)
        assert r2.success

        # Step 3: Non-coercion attestation
        r3 = reops.handle("RE-F07", {"payload": {
            "episodeId": "EP-LC",
        }}, ctx)
        assert r3.success

        # Step 4: Severity score
        r4 = reops.handle("RE-F08", {"payload": {
            "driftType": "process_gap", "severity": "green",
        }}, ctx)
        assert r4.success

        # Step 5: Coherence check
        ctx["coherence_score"] = 85.0
        r5 = reops.handle("RE-F09", {"payload": {
            "episodeId": "EP-LC",
        }}, ctx)
        assert r5.success

        # Step 6: Seal
        r6 = reops.handle("RE-F02", {"payload": {
            "episodeId": "EP-LC",
        }}, ctx)
        assert r6.success
        assert t.get_state("EP-LC") == EpisodeState.SEALED

        # Step 7: Reflection ingest
        r7 = reops.handle("RE-F10", {"payload": {
            "episodeId": "EP-LC",
        }}, ctx)
        assert r7.success

        # Step 8: Archive
        r8 = reops.handle("RE-F03", {"payload": {
            "episodeId": "EP-LC",
        }}, ctx)
        assert r8.success
        assert t.get_state("EP-LC") == EpisodeState.ARCHIVED

        # All replay hashes computed
        assert all(r.replay_hash.startswith("sha256:") for r in [r1, r2, r3, r4, r5, r6, r7, r8])

        # Audit log has entries
        assert log.entry_count >= 3
        assert log.verify_chain()
