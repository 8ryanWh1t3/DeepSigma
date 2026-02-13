"""Integration test — full coherence pipeline end-to-end.

Phase 2 coverage: run episode → seal → coherence report → drift event
→ reconcile / patch → re-run and verify score improvement.

Exercises:
    engine/policy_loader     — load policy pack
    engine/degrade_ladder    — choose degrade step from runtime signals
    engine/supervisor_scaffold — stamp episode with policy + degrade
    coherence_ops.DLRBuilder — build Decision Log Records
    coherence_ops.ReflectionSession — aggregate learning
    coherence_ops.DriftSignalCollector — ingest drift signals
    coherence_ops.MemoryGraph — provenance graph + queries
    coherence_ops.CoherenceScorer — unified 0-100 score
    coherence_ops.CoherenceAuditor — cross-artifact consistency
    coherence_ops.Reconciler — detect and auto-fix inconsistencies
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from engine.policy_loader import load_policy_pack, get_rules
from engine.degrade_ladder import DegradeSignal, choose_degrade_step
from engine.supervisor_scaffold import apply_policy_and_degrade, stamp_episode

from coherence_ops import (
    CoherenceManifest,
    DLRBuilder,
    ReflectionSession,
    DriftSignalCollector,
    MemoryGraph,
    CoherenceAuditor,
    CoherenceScorer,
    Reconciler,
)
from coherence_ops.manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel
from coherence_ops.scoring import CoherenceReport


# ===================================================================
# Fixtures
# ===================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_EPISODES = REPO_ROOT / "coherence_ops" / "examples" / "sample_episodes.json"
SAMPLE_DRIFT = REPO_ROOT / "coherence_ops" / "examples" / "sample_drift.json"
POLICY_PACK = REPO_ROOT / "policy_packs" / "packs" / "demo_policy_pack_v1.json"


@pytest.fixture
def episodes():
    """Load the 3 sample sealed episodes (deploy, scale, rollback)."""
    return json.loads(SAMPLE_EPISODES.read_text())


@pytest.fixture
def drift_events():
    """Load the 5 sample drift events."""
    return json.loads(SAMPLE_DRIFT.read_text())


@pytest.fixture
def manifest():
    """Build a full-coverage CoherenceManifest."""
    m = CoherenceManifest(system_id="integration-test", version="0.1.0")
    for kind in ArtifactKind:
        m.declare(ArtifactDeclaration(
            kind=kind,
            schema_version="1.0.0",
            compliance=ComplianceLevel.FULL,
            source="tests.test_integration",
        ))
    return m


def _build_pipeline(episodes, drift_events):
    """Run the canonical DLR -> RS -> DS -> MG pipeline."""
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    rs = ReflectionSession("rs-integration")
    rs.ingest(episodes)

    ds = DriftSignalCollector()
    if drift_events:
        ds.ingest(drift_events)

    mg = MemoryGraph()
    for ep in episodes:
        mg.add_episode(ep)
    for d in drift_events:
        mg.add_drift(d)

    return dlr, rs, ds, mg


# ===================================================================
# Phase A — Engine: policy load + degrade + stamp
# ===================================================================

class TestEngineIntegration:
    """Engine layer: policy pack -> degrade ladder -> episode stamping."""

    def test_policy_pack_loads(self):
        pack = load_policy_pack(str(POLICY_PACK), verify_hash=False)
        assert pack["policyPackId"]
        assert "rules" in pack

    def test_degrade_step_within_envelope(self):
        signals = DegradeSignal(
            deadline_ms=120, elapsed_ms=50, p99_ms=80,
            jitter_ms=10, ttl_breaches=0,
            max_feature_age_ms=100, verifier_result="pass",
        )
        pack = load_policy_pack(str(POLICY_PACK), verify_hash=False)
        rules = get_rules(pack, "AccountQuarantine")
        ladder = rules["degradeLadder"]
        step, rationale = choose_degrade_step(ladder, signals)
        assert step == "none"
        assert rationale["reason"] == "within_envelope"

    def test_stamp_episode_adds_policy_and_degrade(self):
        signals = DegradeSignal(
            deadline_ms=120, elapsed_ms=95, p99_ms=160,
            jitter_ms=70, ttl_breaches=0,
            max_feature_age_ms=180, verifier_result="pass",
        )
        policy_ref, degrade = apply_policy_and_degrade(
            "AccountQuarantine", str(POLICY_PACK), signals
        )
        episode = {"episodeId": "ep-int-001", "decisionType": "AccountQuarantine"}
        stamped = stamp_episode(episode, policy_ref, degrade)

        assert "policy" in stamped
        assert stamped["policy"]["policyPackId"]
        assert "degrade" in stamped
        assert stamped["degrade"]["step"] in (
            "none", "cache_bundle", "rules_only", "hitl", "abstain"
        )


# ===================================================================
# Phase B — Coherence Ops: full pipeline, score, audit
# ===================================================================

class TestCoherencePipeline:
    """Full DLR -> RS -> DS -> MG -> Score -> Audit pipeline."""

    def test_pipeline_builds_all_four_artifacts(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

        assert len(dlr.entries) == 3
        assert rs.summarise().episode_count == 3
        assert ds.event_count == 5
        stats = mg.query("stats")
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0

    def test_dlr_entries_have_policy_stamps(self, episodes):
        dlr = DLRBuilder()
        dlr.from_episodes(episodes)
        stamped = [e for e in dlr.entries if e.policy_stamp]
        assert len(stamped) == len(episodes), (
            "Every sample episode should produce a DLR entry with a policy stamp"
        )

    def test_reflection_session_produces_takeaways(self, episodes):
        rs = ReflectionSession("rs-int-test")
        rs.ingest(episodes)
        summary = rs.summarise()
        assert summary.episode_count == 3
        assert len(summary.takeaways) > 0
        assert summary.verification_pass_rate < 1.0, (
            "ep-demo-003 has a verification fail, so pass rate < 1.0"
        )

    def test_drift_collector_buckets_by_fingerprint(self, drift_events):
        ds = DriftSignalCollector()
        ds.ingest(drift_events)
        summary = ds.summarise()
        assert summary.total_signals == 5
        assert summary.by_severity.get("red", 0) == 3
        assert len(summary.top_recurring) >= 1

    def test_memory_graph_why_query(self, episodes, drift_events):
        _, _, _, mg = _build_pipeline(episodes, drift_events)
        why = mg.query("why", episode_id="ep-demo-003")
        assert why.get("node") is not None
        assert "evidence_refs" in why

    def test_memory_graph_drift_query(self, episodes, drift_events):
        _, _, _, mg = _build_pipeline(episodes, drift_events)
        drift_q = mg.query("drift", episode_id="ep-demo-003")
        assert "drift_events" in drift_q
        assert len(drift_q["drift_events"]) > 0


# ===================================================================
# Phase C — Scoring: coherence score + grades
# ===================================================================

class TestCoherenceScoring:
    """Unified 0-100 coherence score with dimension breakdown."""

    def test_healthy_episodes_score_high(self, episodes):
        healthy = [ep for ep in episodes if ep["outcome"]["code"] == "success"]
        dlr, rs, ds, mg = _build_pipeline(healthy, [])

        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()

        assert isinstance(report, CoherenceReport)
        assert 70 <= report.overall_score <= 100, (
            f"Healthy episodes should score 70+, got {report.overall_score}"
        )
        assert report.grade in ("A", "B")
        assert len(report.dimensions) == 4

    def test_stress_path_scores_lower(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()

        assert report.overall_score < 85, (
            f"All drift + partial outcomes should pull score below 85, "
            f"got {report.overall_score}"
        )

    def test_score_improves_after_removing_drift(self, episodes, drift_events):
        """Core integration assertion: removing drift should improve the score."""
        # Run 1 — with all drift
        dlr1, rs1, ds1, mg1 = _build_pipeline(episodes, drift_events)
        score_before = CoherenceScorer(
            dlr_builder=dlr1, rs=rs1, ds=ds1, mg=mg1
        ).score().overall_score

        # Run 2 — with only green drift (remove red + yellow)
        mild = [d for d in drift_events if d["severity"] == "green"]
        dlr2, rs2, ds2, mg2 = _build_pipeline(episodes, mild)
        score_after = CoherenceScorer(
            dlr_builder=dlr2, rs=rs2, ds=ds2, mg=mg2
        ).score().overall_score

        assert score_after > score_before, (
            f"Removing red/yellow drift should improve score: "
            f"{score_before} -> {score_after}"
        )

    def test_score_json_serializable(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        raw = json.loads(scorer.to_json())
        assert "overall_score" in raw
        assert "dimensions" in raw
        assert len(raw["dimensions"]) == 4


# ===================================================================
# Phase D — Audit: cross-artifact consistency
# ===================================================================

class TestCoherenceAudit:
    """CoherenceAuditor cross-artifact consistency checks."""

    def test_audit_runs_and_produces_findings(
        self, episodes, drift_events, manifest
    ):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        auditor = CoherenceAuditor(
            manifest=manifest, dlr_builder=dlr, rs=rs, ds=ds, mg=mg
        )
        report = auditor.run("audit-int-001")

        assert report.run_at is not None
        assert isinstance(report.findings, list)
        assert report.summary  # non-empty summary string

    def test_audit_detects_verification_failure(
        self, episodes, drift_events, manifest
    ):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        auditor = CoherenceAuditor(
            manifest=manifest, dlr_builder=dlr, rs=rs, ds=ds, mg=mg
        )
        report = auditor.run("audit-int-002")

        # ep-demo-003 has verification: fail — auditor should flag it
        assert len(report.findings) > 0, (
            "Auditor should detect at least one finding "
            "(ep-demo-003 verification failure)"
        )


# ===================================================================
# Phase E — Reconciler: detect + auto-fix inconsistencies
# ===================================================================

class TestReconciler:
    """Reconciler detects and proposes repairs for cross-artifact gaps."""

    def test_reconcile_with_full_pipeline(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        recon = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
        result = recon.reconcile()

        assert result.run_at is not None
        assert isinstance(result.proposals, list)

    def test_reconcile_detects_recurring_drift(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        recon = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
        result = recon.reconcile()

        patch_proposals = [
            p for p in result.proposals if p.kind.value == "suggest_patch"
        ]
        assert len(patch_proposals) >= 1, (
            "verify:smoke-test-v1:fail recurs 3x — reconciler should suggest patch"
        )

    def test_reconcile_json_serializable(self, episodes, drift_events):
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
        recon = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
        raw = json.loads(recon.to_json())
        assert "proposals" in raw
        assert "auto_fixable_count" in raw


# ===================================================================
# Phase F — End-to-End: episode → score → drift → patch → re-score
# ===================================================================

class TestEndToEnd:
    """The full coverage loop: episode → seal → report → drift → patch → re-run."""

    def test_full_lifecycle(self, episodes, drift_events, manifest):
        # ---- Step 1: Run initial pipeline with episodes only (pre-drift) ----
        healthy = [ep for ep in episodes if ep["outcome"]["code"] == "success"]
        dlr0, rs0, ds0, mg0 = _build_pipeline(healthy, [])
        score_baseline = CoherenceScorer(
            dlr_builder=dlr0, rs=rs0, ds=ds0, mg=mg0
        ).score()

        assert score_baseline.overall_score > 0
        assert score_baseline.grade in ("A", "B", "C", "D", "F")

        # ---- Step 2: Introduce drift events (simulate production) ----
        dlr1, rs1, ds1, mg1 = _build_pipeline(episodes, drift_events)
        score_with_drift = CoherenceScorer(
            dlr_builder=dlr1, rs=rs1, ds=ds1, mg=mg1
        ).score()

        assert score_with_drift.overall_score < score_baseline.overall_score, (
            "Adding verification failures and red drift should lower score"
        )

        # ---- Step 3: Run audit — should detect issues ----
        auditor = CoherenceAuditor(
            manifest=manifest, dlr_builder=dlr1, rs=rs1, ds=ds1, mg=mg1
        )
        audit_report = auditor.run("audit-lifecycle-001")
        assert len(audit_report.findings) > 0

        # ---- Step 4: Run reconciler — should propose patches ----
        recon = Reconciler(dlr_builder=dlr1, ds=ds1, mg=mg1)
        recon_result = recon.reconcile()
        assert len(recon_result.proposals) > 0

        # ---- Step 5: Simulate patching (remove red drift, keep green) ----
        patched_drift = [d for d in drift_events if d["severity"] == "green"]
        dlr2, rs2, ds2, mg2 = _build_pipeline(episodes, patched_drift)
        score_after_patch = CoherenceScorer(
            dlr_builder=dlr2, rs=rs2, ds=ds2, mg=mg2
        ).score()

        assert score_after_patch.overall_score > score_with_drift.overall_score, (
            f"Patching drift should improve score: "
            f"{score_with_drift.overall_score} -> {score_after_patch.overall_score}"
        )

        # ---- Step 6: Memory Graph retains full provenance ----
        why = mg2.query("why", episode_id="ep-demo-003")
        assert why.get("node") is not None, (
            "Rollback episode should still exist in Memory Graph after patching"
        )

    def test_engine_to_coherence_bridge(self, episodes, drift_events, manifest):
        """Verify that engine-stamped episodes feed correctly into coherence_ops."""
        # Stamp an episode through the engine layer
        signals = DegradeSignal(
            deadline_ms=120, elapsed_ms=50, p99_ms=80,
            jitter_ms=10, ttl_breaches=0,
            max_feature_age_ms=100, verifier_result="pass",
        )
        policy_ref, degrade = apply_policy_and_degrade(
            "AccountQuarantine", str(POLICY_PACK), signals
        )
        engine_episode = {
            "episodeId": "ep-engine-bridge-001",
            "decisionType": "AccountQuarantine",
            "sealedAt": datetime.now(timezone.utc).isoformat(),
            "actions": [{"type": "test_action", "blastRadiusTier": "low"}],
            "verification": {"result": "pass", "verifierId": "bridge-test"},
            "outcome": {"code": "success", "detail": "engine bridge test"},
            "seal": {"sealHash": "sha256:bridge001", "sealedAt": datetime.now(timezone.utc).isoformat()},
            "context": {"evidenceRefs": ["evidence:bridge-test"]},
        }
        stamped = stamp_episode(engine_episode, policy_ref, degrade)

        # Feed the engine-stamped episode into coherence_ops
        combined = episodes + [stamped]
        dlr, rs, ds, mg = _build_pipeline(combined, drift_events)

        # The engine episode should appear in DLR
        engine_dlr = [e for e in dlr.entries if e.episode_id == "ep-engine-bridge-001"]
        assert len(engine_dlr) == 1, "Engine-stamped episode should appear in DLR"

        # Should appear in Memory Graph
        why = mg.query("why", episode_id="ep-engine-bridge-001")
        assert why.get("node") is not None

        # Score should still compute with the extra episode
        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()
        assert report.overall_score > 0
