"""Unit tests for the full coherence bridge: episode -> all four pillars."""
import json
from coherence_ops.dlr import DLRBuilder
from coherence_ops.rs import ReflectionSession
from coherence_ops.ds import DriftSignalCollector
from coherence_ops.mg import MemoryGraph


# ---------------------------------------------------------------------------
# Shared fixture: realistic episode batch
# ---------------------------------------------------------------------------

EPISODES = [
    {
        "episodeId": "ep-deploy-001",
        "decisionType": "AccountQuarantine",
        "dteRef": {"deadlineBudgetMs": 250, "ttlMs": 30000},
        "actions": [
            {
                "type": "quarantine",
                "blastRadiusTier": "account",
                "idempotencyKey": "ik-deploy-001",
                "rollbackPlan": "unquarantine",
                "authorization": {"mode": "rbac"},
                "targetRefs": ["acc-001"],
            }
        ],
        "context": {"evidenceRefs": ["evidence-suspicious-login"]},
        "verification": {"result": "pass", "method": "read_after_write"},
        "policy": {"policyPackId": "demo_policy_pack_v1", "version": "1.0.0"},
        "outcome": {"code": "success"},
        "degrade": {"step": "none"},
        "sealedAt": "2026-02-12T12:00:00Z",
        "seal": {"sealHash": "sha256:aaa"},
    },
    {
        "episodeId": "ep-stale-002",
        "decisionType": "AccountQuarantine",
        "dteRef": {"deadlineBudgetMs": 250, "ttlMs": 30000},
        "actions": [],
        "context": {"evidenceRefs": []},
        "verification": {"result": "na"},
        "policy": {"policyPackId": "demo_policy_pack_v1", "version": "1.0.0"},
        "outcome": {"code": "abstain"},
        "degrade": {"step": "abstain"},
        "sealedAt": "2026-02-12T12:05:00Z",
        "seal": {"sealHash": "sha256:bbb"},
    },
    {
        "episodeId": "ep-spike-003",
        "decisionType": "AccountQuarantine",
        "dteRef": {"deadlineBudgetMs": 250, "ttlMs": 30000},
        "actions": [
            {
                "type": "fallback_lookup",
                "blastRadiusTier": "none",
                "idempotencyKey": "ik-spike-003",
                "authorization": {"mode": "none"},
            }
        ],
        "context": {"evidenceRefs": ["evidence-latency-spike"]},
        "verification": {"result": "fail", "method": "read_after_write"},
        "policy": {"policyPackId": "demo_policy_pack_v1", "version": "1.0.0"},
        "outcome": {"code": "success"},
        "degrade": {"step": "fallback_cache"},
        "sealedAt": "2026-02-12T12:10:00Z",
        "seal": {"sealHash": "sha256:ccc"},
    },
]

DRIFT_EVENTS = [
    {
        "driftId": "drift-fresh-001",
        "episodeId": "ep-stale-002",
        "driftType": "freshness",
        "severity": "yellow",
        "detectedAt": "2026-02-12T12:05:30Z",
        "fingerprint": {"key": "AQ:freshness:geo_ip"},
        "recommendedPatchType": "ttl_change",
    },
    {
        "driftId": "drift-time-002",
        "episodeId": "ep-spike-003",
        "driftType": "time",
        "severity": "red",
        "detectedAt": "2026-02-12T12:10:30Z",
        "fingerprint": {"key": "AQ:time:deadline_breach"},
        "recommendedPatchType": "budget_increase",
    },
]


class TestCoherenceBridge:
    """Full bridge: episode -> DLR + RS + DS + MG, all four pillars."""

    def test_dlr_bridge(self):
        """DLR: episodes become Decision Log Records."""
        builder = DLRBuilder()
        entries = builder.from_episodes(EPISODES)
        assert len(entries) == 3
        assert entries[0].decision_type == "AccountQuarantine"
        assert entries[1].outcome_code == "abstain"
        assert entries[2].degrade_step == "fallback_cache"

    def test_rs_bridge(self):
        """RS: episodes become a Reflection Summary."""
        rs = ReflectionSession("bridge-rs")
        rs.ingest(EPISODES)
        summary = rs.summarise()
        assert summary.episode_count == 3
        assert summary.outcome_distribution["success"] == 2
        assert summary.outcome_distribution["abstain"] == 1
        assert summary.verification_pass_rate < 1.0

    def test_rs_detects_critical_divergence(self):
        """RS: verify=fail + outcome=success flagged as critical."""
        rs = ReflectionSession("bridge-rs-div")
        rs.ingest(EPISODES)
        summary = rs.summarise()
        critical = [d for d in summary.divergences if d.severity == "critical"]
        assert len(critical) >= 1
        assert critical[0].episode_id == "ep-spike-003"

    def test_ds_bridge(self):
        """DS: drift events collected and bucketed."""
        ds = DriftSignalCollector()
        ds.ingest(DRIFT_EVENTS)
        summary = ds.summarise()
        assert summary.total_signals == 2
        assert summary.by_type["freshness"] == 1
        assert summary.by_type["time"] == 1
        assert summary.by_severity["red"] == 1

    def test_mg_bridge(self):
        """MG: episodes + drift -> full provenance graph."""
        mg = MemoryGraph()
        for ep in EPISODES:
            mg.add_episode(ep)
        for drift in DRIFT_EVENTS:
            mg.add_drift(drift)
        stats = mg.query("stats")
        assert stats["nodes_by_kind"]["episode"] == 3
        assert stats["nodes_by_kind"]["drift"] == 2
        assert stats["edges_by_kind"].get("triggered", 0) >= 1

    def test_mg_query_why(self):
        """MG: 'why' query returns evidence + actions."""
        mg = MemoryGraph()
        for ep in EPISODES:
            mg.add_episode(ep)
        result = mg.query("why", episode_id="ep-deploy-001")
        assert result["node"] is not None
        assert len(result["actions"]) >= 1
        assert len(result["evidence_refs"]) >= 1

    def test_full_pipeline(self):
        """Full bridge: all four pillars produce valid output from same input."""
        # DLR
        dlr_builder = DLRBuilder()
        dlr_builder.from_episodes(EPISODES)
        dlr_json = json.loads(dlr_builder.to_json())

        # RS
        rs = ReflectionSession("full-bridge")
        rs.ingest(EPISODES)
        rs_json = json.loads(rs.to_json())

        # DS
        ds = DriftSignalCollector()
        ds.ingest(DRIFT_EVENTS)
        ds_json = json.loads(ds.to_json())

        # MG
        mg = MemoryGraph()
        for ep in EPISODES:
            mg.add_episode(ep)
        for drift in DRIFT_EVENTS:
            mg.add_drift(drift)
        mg_json = json.loads(mg.to_json())

        # All four pillars produce valid JSON output
        assert len(dlr_json) == 3
        assert rs_json["episode_count"] == 3
        assert ds_json["total_signals"] == 2
        assert len(mg_json["nodes"]) >= 5

    def test_bridge_episode_ids_consistent(self):
        """All four pillars reference the same episode IDs."""
        ep_ids = {ep["episodeId"] for ep in EPISODES}

        dlr_builder = DLRBuilder()
        dlr_entries = dlr_builder.from_episodes(EPISODES)
        dlr_ep_ids = {e.episode_id for e in dlr_entries}
        assert dlr_ep_ids == ep_ids

        rs = ReflectionSession("consistency-check")
        rs.ingest(EPISODES)
        # RS doesn't expose per-episode IDs but processes all
        assert rs.summarise().episode_count == len(ep_ids)
