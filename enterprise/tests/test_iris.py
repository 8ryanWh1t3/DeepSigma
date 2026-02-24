"""Tests for the IRIS operator query resolution engine.

Covers all 5 query resolvers, confidence scoring, provenance assembly,
SLA warnings, response serialisation, config validation, and CLI routing.
All artifact dependencies are mocked — no live data or API calls needed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from core.iris import (
    IRISConfig,
    IRISEngine,
    IRISQuery,
    IRISResponse,
    QueryType,
    ResolutionStatus,
)


# ---------------------------------------------------------------------------
# Fixtures — mock artifacts
# ---------------------------------------------------------------------------

def _mock_mg(
    why: Dict[str, Any] | None = None,
    claims: List[Dict[str, Any]] | None = None,
    drift_events: List[Dict[str, Any]] | None = None,
    patches: List[Dict[str, Any]] | None = None,
    stats: Dict[str, Any] | None = None,
    claim: Dict[str, Any] | None = None,
) -> MagicMock:
    """Build a MemoryGraph mock with configurable query returns."""
    default_why = {"node": {"episode_id": "ep-001"}, "evidence_refs": ["ev-1", "ev-2"],
                   "actions": ["act-1"], "context": {}}
    default_stats = {"total_nodes": 10, "total_edges": 8,
                     "nodes_by_kind": {"episode": 3, "claim": 4, "drift": 2, "patch": 1}}
    default_claim = {"node": {"node_id": "cl-001", "label": "service is healthy"},
                     "evidence": ["ev-1"], "patches": [], "supersedes": []}

    mg = MagicMock()

    def _query(mode: str, **kwargs: Any) -> Dict[str, Any]:
        if mode == "why":
            return why if why is not None else default_why
        if mode == "claims":
            return {"claims": claims if claims is not None else []}
        if mode == "drift":
            return {"drift_events": drift_events if drift_events is not None else []}
        if mode == "patches":
            return {"patches": patches if patches is not None else []}
        if mode == "stats":
            return stats if stats is not None else default_stats
        if mode == "claim":
            return claim if claim is not None else default_claim
        return {}

    mg.query.side_effect = _query
    return mg


def _mock_dlr_entry(
    episode_id: str = "ep-001",
    decision_type: str = "AccountQuarantine",
    outcome_code: str = "success",
    degrade_step: str | None = None,
    policy_stamp: Dict[str, Any] | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.episode_id = episode_id
    entry.dlr_id = f"dlr-{episode_id}"
    entry.decision_type = decision_type
    entry.outcome_code = outcome_code
    entry.degrade_step = degrade_step
    entry.policy_stamp = policy_stamp or {"policyPackId": "pp-v1", "version": "1.0.0"}
    entry.verification = {"method": "read_after_write", "outcome": "pass"}
    entry.action_contract = {"blastRadiusTier": "small"}
    return entry


def _mock_rs(episode_count: int = 3, pass_rate: float = 0.9) -> MagicMock:
    rs = MagicMock()
    summary = MagicMock()
    summary.episode_count = episode_count
    summary.outcome_distribution = {"success": episode_count - 1, "fail": 1}
    summary.verification_pass_rate = pass_rate
    rs.summarise.return_value = summary
    return rs


def _mock_ds(
    total: int = 4,
    by_severity: Dict[str, int] | None = None,
    by_type: Dict[str, int] | None = None,
    top_recurring: List[str] | None = None,
    buckets: List[Any] | None = None,
) -> MagicMock:
    ds = MagicMock()
    ds.event_count = total
    summary = MagicMock()
    summary.total_signals = total
    summary.by_severity = by_severity or {"green": 1, "yellow": 2, "red": 1}
    summary.by_type = by_type or {"freshness": 2, "verify": 1, "time": 1}
    summary.top_recurring = top_recurring or ["fp-key-001"]
    if buckets is None:
        b = MagicMock()
        b.fingerprint_key = "fp-key-001"
        b.drift_type = "freshness"
        b.count = 2
        b.worst_severity = "yellow"
        b.recommended_patches = ["ttl_change"]
        buckets = [b]
    summary.buckets = buckets
    ds.summarise.return_value = summary
    return ds


def _engine(mg=None, dlr_entries=None, rs=None, ds=None,
            config: IRISConfig | None = None) -> IRISEngine:
    return IRISEngine(
        config=config or IRISConfig(),
        memory_graph=mg or _mock_mg(),
        dlr_entries=dlr_entries,
        rs=rs,
        ds=ds,
    )


# ---------------------------------------------------------------------------
# 1. WHY resolver
# ---------------------------------------------------------------------------

class TestResolveWhy:
    def test_why_with_valid_episode(self):
        """Happy path: MG + DLR both match → RESOLVED, confidence ≥ 0.85."""
        dlr = [_mock_dlr_entry("ep-001")]
        rs = _mock_rs()
        eng = _engine(dlr_entries=dlr, rs=rs)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.status == ResolutionStatus.RESOLVED
        assert resp.confidence >= 0.85
        assert "dlr_entry" in resp.data
        assert resp.data["dlr_entry"]["decision_type"] == "AccountQuarantine"
        assert resp.data["dlr_entry"]["outcome_code"] == "success"
        assert "rs_context" in resp.data

    def test_why_mg_only(self):
        """MG found, no DLR/RS → RESOLVED with lower confidence."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.status == ResolutionStatus.RESOLVED
        assert resp.confidence == pytest.approx(0.50)

    def test_why_missing_episode(self):
        """MG returns no node → NOT_FOUND."""
        mg = _mock_mg(why={"node": None, "evidence_refs": []})
        eng = _engine(mg=mg)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-missing"))
        assert resp.status == ResolutionStatus.NOT_FOUND
        assert resp.confidence == 0.0

    def test_why_requires_id(self):
        """WHY without episode_id or claim_id → ERROR."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY))
        assert resp.status == ResolutionStatus.ERROR

    def test_why_claim_id_path(self):
        """WHY with claim_id queries claim node."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, claim_id="cl-001"))
        assert resp.status == ResolutionStatus.RESOLVED
        assert "mg_claim" in resp.data

    def test_why_provenance_includes_dlr(self):
        """Provenance chain contains DLR link when DLR entry found."""
        dlr = [_mock_dlr_entry("ep-001")]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        artifacts = [p["artifact"] for p in resp.provenance]
        assert "DLR" in artifacts


# ---------------------------------------------------------------------------
# 2. WHAT_CHANGED resolver
# ---------------------------------------------------------------------------

class TestResolveWhatChanged:
    def test_what_changed_with_dlr_and_patches(self):
        """Happy path: DLR entries + MG patches → RESOLVED."""
        dlr = [_mock_dlr_entry("ep-001")]
        mg = _mock_mg(patches=[{"patch_id": "p-1", "type": "ttl_change"}])
        eng = _engine(mg=mg, dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED, episode_id="ep-001"))
        assert resp.status == ResolutionStatus.RESOLVED
        assert "dlr_summary" in resp.data
        assert "patches" in resp.data

    def test_what_changed_outcome_distribution(self):
        """DLR entries produce outcome distribution."""
        dlr = [
            _mock_dlr_entry("ep-001", outcome_code="success"),
            _mock_dlr_entry("ep-002", outcome_code="fail"),
            _mock_dlr_entry("ep-003", outcome_code="success"),
        ]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED))
        dist = resp.data["dlr_summary"]["outcome_distribution"]
        assert dist["success"] == 2
        assert dist["fail"] == 1

    def test_what_changed_degraded_episodes_detected(self):
        """DLR entries with degrade_step appear in degraded_episodes list."""
        dlr = [
            _mock_dlr_entry("ep-001", degrade_step="rules_only"),
            _mock_dlr_entry("ep-002"),
        ]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED))
        assert "ep-001" in resp.data["dlr_summary"]["degraded_episodes"]
        assert "ep-002" not in resp.data["dlr_summary"]["degraded_episodes"]

    def test_what_changed_policy_missing_detected(self):
        """DLR entry with no policy_stamp appears in policy_missing list."""
        dlr = [_mock_dlr_entry("ep-001", policy_stamp=None)]
        entry = dlr[0]
        entry.policy_stamp = None
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED))
        assert "ep-001" in resp.data["dlr_summary"]["policy_missing"]

    def test_what_changed_ds_drift_summary_included(self):
        """DS drift summary appears when DS is wired."""
        ds = _mock_ds(total=3)
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED))
        assert "drift_summary" in resp.data
        assert resp.data["drift_summary"]["total_signals"] == 3

    def test_what_changed_no_data(self):
        """Empty DLR + no patches + no DS → NOT_FOUND."""
        mg = _mock_mg(patches=[])
        eng = _engine(mg=mg)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_CHANGED))
        assert resp.status == ResolutionStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# 3. WHAT_DRIFTED resolver
# ---------------------------------------------------------------------------

class TestResolveWhatDrifted:
    def test_what_drifted_severity_breakdown(self):
        """DS signals produce by_severity breakdown."""
        ds = _mock_ds(total=4, by_severity={"green": 1, "yellow": 2, "red": 1})
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        assert resp.status == ResolutionStatus.RESOLVED
        assert resp.data["by_severity"]["red"] == 1
        assert resp.data["by_severity"]["yellow"] == 2

    def test_what_drifted_resolution_ratio(self):
        """Resolution ratio = MG patch_nodes / total drift signals."""
        ds = _mock_ds(total=4)
        mg = _mock_mg(stats={"total_nodes": 10, "total_edges": 8,
                              "nodes_by_kind": {"drift": 4, "patch": 2, "episode": 3}})
        eng = _engine(mg=mg, ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        assert resp.data["resolution_ratio"] == pytest.approx(2 / 4)

    def test_what_drifted_top_buckets_present(self):
        """Top fingerprint buckets from DS summary included in data."""
        ds = _mock_ds()
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        assert "top_buckets" in resp.data
        assert len(resp.data["top_buckets"]) > 0
        bucket = resp.data["top_buckets"][0]
        assert "fingerprint_key" in bucket
        assert "drift_type" in bucket

    def test_what_drifted_top_recurring(self):
        """Recurring fingerprint keys from DS summary included."""
        ds = _mock_ds(top_recurring=["fp-key-001", "fp-key-002"])
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        assert "fp-key-001" in resp.data["top_recurring"]

    def test_what_drifted_no_signals(self):
        """No DS and empty MG drift nodes → NOT_FOUND."""
        ds = MagicMock()
        ds.event_count = 0
        mg = _mock_mg(stats={"total_nodes": 5, "total_edges": 3,
                              "nodes_by_kind": {"episode": 2, "drift": 0, "patch": 0}})
        eng = _engine(mg=mg, ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        assert resp.status == ResolutionStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# 4. RECALL resolver
# ---------------------------------------------------------------------------

class TestResolveRecall:
    def test_recall_full_graph(self):
        """Happy path: MG graph walk + DLR enrichment → RESOLVED."""
        dlr = [_mock_dlr_entry("ep-001")]
        mg = _mock_mg(
            drift_events=[{"node_id": "dr-1", "driftType": "freshness"}],
            patches=[{"patch_id": "p-1"}],
            claims=[{"node_id": "cl-1", "label": "healthy"}],
        )
        eng = _engine(mg=mg, dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.RECALL, episode_id="ep-001"))
        assert resp.status == ResolutionStatus.RESOLVED
        assert "provenance" in resp.data
        assert "drift_events" in resp.data
        assert "patches" in resp.data
        assert "claims" in resp.data
        assert "dlr_entry" in resp.data

    def test_recall_missing_episode(self):
        """MG returns no node → NOT_FOUND."""
        mg = _mock_mg(why={"node": None, "evidence_refs": []})
        eng = _engine(mg=mg)
        resp = eng.resolve(IRISQuery(query_type=QueryType.RECALL, episode_id="ep-missing"))
        assert resp.status == ResolutionStatus.NOT_FOUND

    def test_recall_requires_episode_id(self):
        """RECALL without episode_id → ERROR."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.RECALL))
        assert resp.status == ResolutionStatus.ERROR

    def test_recall_dlr_fields_populated(self):
        """DLR entry fields (decision_type, outcome_code, verification) in data."""
        dlr = [_mock_dlr_entry("ep-001", decision_type="FraudReview", outcome_code="fail")]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.RECALL, episode_id="ep-001"))
        dlr_data = resp.data["dlr_entry"]
        assert dlr_data["decision_type"] == "FraudReview"
        assert dlr_data["outcome_code"] == "fail"
        assert dlr_data["verification"] is not None


# ---------------------------------------------------------------------------
# 5. STATUS resolver
# ---------------------------------------------------------------------------

class TestResolveStatus:
    def test_status_coherence_score_returned(self):
        """CoherenceScorer is called; overall_score and grade in data."""
        eng = _engine(dlr_entries=[_mock_dlr_entry("ep-001")], rs=_mock_rs(), ds=_mock_ds())
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert resp.status == ResolutionStatus.RESOLVED
        assert "overall_score" in resp.data
        assert "grade" in resp.data
        assert isinstance(resp.data["overall_score"], float)

    def test_status_dimensions_present(self):
        """Four dimension scores with name, score, weight fields."""
        eng = _engine(dlr_entries=[_mock_dlr_entry()], rs=_mock_rs(), ds=_mock_ds())
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        dims = resp.data.get("dimensions", [])
        assert len(dims) == 4
        names = {d["name"] for d in dims}
        assert "policy_adherence" in names
        assert "drift_control" in names

    def test_status_drift_headline_included(self):
        """DS drift_headline (total, red, recurring) in data."""
        ds = _mock_ds(total=5, by_severity={"red": 2, "yellow": 2, "green": 1})
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert "drift_headline" in resp.data
        assert resp.data["drift_headline"]["total"] == 5
        assert resp.data["drift_headline"]["red"] == 2

    def test_status_mg_stats_included(self):
        """MG stats included in STATUS data."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert "mg_stats" in resp.data
        assert resp.data["mg_stats"]["total_nodes"] == 10

    def test_status_summary_contains_score(self):
        """Summary string mentions coherence score and grade."""
        eng = _engine(dlr_entries=[_mock_dlr_entry()], rs=_mock_rs(), ds=_mock_ds())
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert "/100" in resp.summary


# ---------------------------------------------------------------------------
# 6. Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_confidence_mg_only(self):
        """MG-only WHY → confidence = 0.50."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.confidence == pytest.approx(0.50)

    def test_confidence_mg_plus_dlr(self):
        """MG + DLR WHY → confidence = 0.85 (0.50 + 0.35)."""
        dlr = [_mock_dlr_entry("ep-001")]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.confidence == pytest.approx(0.85)

    def test_confidence_all_artifacts_capped_at_1(self):
        """Summed confidence never exceeds 1.0."""
        dlr = [_mock_dlr_entry("ep-001")]
        rs = _mock_rs()
        ds = _mock_ds()
        eng = _engine(dlr_entries=dlr, rs=rs, ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.confidence <= 1.0

    def test_confidence_zero_returns_not_found(self):
        """Confidence 0.0 maps to NOT_FOUND status."""
        mg = _mock_mg(why={"node": None, "evidence_refs": []})
        eng = _engine(mg=mg)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-missing"))
        assert resp.status == ResolutionStatus.NOT_FOUND
        assert resp.confidence == 0.0

    def test_confidence_partial_threshold(self):
        """Confidence > 0 and < 0.5 maps to PARTIAL."""
        from core.iris import IRISEngine
        assert IRISEngine._status(0.3) == ResolutionStatus.PARTIAL
        assert IRISEngine._status(0.49) == ResolutionStatus.PARTIAL

    def test_confidence_resolved_threshold(self):
        """Confidence ≥ 0.5 maps to RESOLVED."""
        from core.iris import IRISEngine
        assert IRISEngine._status(0.5) == ResolutionStatus.RESOLVED
        assert IRISEngine._status(1.0) == ResolutionStatus.RESOLVED


# ---------------------------------------------------------------------------
# 7. Provenance chain
# ---------------------------------------------------------------------------

class TestProvenanceChain:
    def test_provenance_has_mg_link(self):
        """MG link present in WHY provenance when episode found."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        artifacts = [p["artifact"] for p in resp.provenance]
        assert "MG" in artifacts

    def test_provenance_has_dlr_link(self):
        """DLR link present when DLR entry matches."""
        dlr = [_mock_dlr_entry("ep-001")]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        artifacts = [p["artifact"] for p in resp.provenance]
        assert "DLR" in artifacts

    def test_provenance_link_roles(self):
        """Each provenance link has artifact, ref_id, role, detail fields."""
        dlr = [_mock_dlr_entry("ep-001")]
        eng = _engine(dlr_entries=dlr)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        for link in resp.provenance:
            assert "artifact" in link
            assert "ref_id" in link
            assert "role" in link
            assert "detail" in link
            assert link["role"] in ("source", "evidence", "context")

    def test_provenance_empty_on_not_found(self):
        """Provenance chain is empty when episode not found."""
        mg = _mock_mg(why={"node": None, "evidence_refs": []})
        eng = _engine(mg=mg)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-missing"))
        assert resp.provenance == []

    def test_provenance_ds_link_in_what_drifted(self):
        """DS link present in WHAT_DRIFTED provenance."""
        ds = _mock_ds()
        eng = _engine(ds=ds)
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHAT_DRIFTED))
        artifacts = [p["artifact"] for p in resp.provenance]
        assert "DS" in artifacts


# ---------------------------------------------------------------------------
# 8. Configuration & SLA
# ---------------------------------------------------------------------------

class TestConfigAndSLA:
    def test_config_validate_valid(self):
        """Valid config produces no issues."""
        cfg = IRISConfig(response_time_target_ms=30_000)
        assert cfg.validate() == []

    def test_config_validate_zero(self):
        """response_time_target_ms=0 is invalid."""
        cfg = IRISConfig(response_time_target_ms=0)
        issues = cfg.validate()
        assert len(issues) == 1
        assert "positive" in issues[0]

    def test_config_validate_negative(self):
        """Negative response_time_target_ms is invalid."""
        with pytest.raises(ValueError, match="IRISConfig"):
            IRISEngine(config=IRISConfig(response_time_target_ms=-1))

    def test_sla_warning_on_slow_query(self):
        """Warning added when elapsed_ms exceeds response_time_target_ms."""
        eng = IRISEngine(config=IRISConfig(response_time_target_ms=1),
                         memory_graph=_mock_mg())
        with patch.object(IRISEngine, "_elapsed", staticmethod(lambda _: 99999.0)):
            resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert any("exceeded" in w for w in resp.warnings)

    def test_no_sla_warning_on_fast_query(self):
        """No SLA warning when query finishes within target."""
        eng = _engine(config=IRISConfig(response_time_target_ms=60_000))
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert not any("exceeded" in w for w in resp.warnings)

    def test_no_mg_returns_error(self):
        """Engine without MemoryGraph returns ERROR status."""
        eng = IRISEngine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.WHY, episode_id="ep-001"))
        assert resp.status == ResolutionStatus.ERROR


# ---------------------------------------------------------------------------
# 9. Response format
# ---------------------------------------------------------------------------

class TestResponseFormat:
    def test_response_has_query_id_format(self):
        """query_id matches iris-{12 hex chars} pattern."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert re.match(r"^iris-[0-9a-f]{12}$", resp.query_id)

    def test_response_serialisation(self):
        """to_dict() produces JSON-serialisable dict with all required keys."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        d = resp.to_dict()
        serialised = json.dumps(d)  # must not raise
        parsed = json.loads(serialised)
        for key in ("query_id", "query_type", "status", "summary",
                    "data", "provenance", "confidence", "warnings", "elapsed_ms"):
            assert key in parsed

    def test_response_elapsed_ms_positive(self):
        """elapsed_ms is > 0 after resolve()."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type=QueryType.STATUS))
        assert resp.elapsed_ms > 0

    def test_confidence_clamped_in_response(self):
        """IRISResponse clamps confidence to [0.0, 1.0]."""
        r = IRISResponse("id", "WHY", ResolutionStatus.RESOLVED, "ok", confidence=1.5)
        assert r.confidence == pytest.approx(1.0)
        r2 = IRISResponse("id", "WHY", ResolutionStatus.NOT_FOUND, "ok", confidence=-0.3)
        assert r2.confidence == pytest.approx(0.0)

    def test_unknown_query_type_returns_error(self):
        """Unrecognised query type returns ERROR with supported types hint."""
        eng = _engine()
        resp = eng.resolve(IRISQuery(query_type="BOGUS"))
        assert resp.status == ResolutionStatus.ERROR
        assert any("BOGUS" in w or "WHY" in w for w in [resp.summary] + resp.warnings)


# ---------------------------------------------------------------------------
# 10. CLI routing
# ---------------------------------------------------------------------------

class TestCLI:
    def _run_cli(self, args: List[str]) -> int:
        """Run the CLI main() and return exit code (0 = success)."""
        import sys
        from core.cli import main
        old_argv = sys.argv
        sys.argv = ["coherence"] + args
        try:
            main()
            return 0
        except SystemExit as e:
            return int(e.code) if e.code is not None else 0
        finally:
            sys.argv = old_argv

    def test_cli_status_query(self, tmp_path, capsys):
        """CLI STATUS query completes and prints summary."""
        ep_file = tmp_path / "ep.json"
        ep_file.write_text(json.dumps([{
            "episodeId": "ep-001",
            "decisionType": "Demo",
            "outcome": {"code": "success"},
            "degrade": {},
            "policy": {"policyPackId": "pp-1"},
        }]))
        rc = self._run_cli(["iris", "query", str(ep_file), "--type", "STATUS"])
        assert rc == 0
        out = capsys.readouterr().out
        assert len(out) > 0

    def test_cli_why_requires_target(self, tmp_path, capsys):
        """CLI WHY without --target exits with code 1."""
        ep_file = tmp_path / "ep.json"
        ep_file.write_text(json.dumps([{"episodeId": "ep-001", "decisionType": "Demo",
                                        "outcome": {"code": "success"}, "degrade": {}}]))
        rc = self._run_cli(["iris", "query", str(ep_file), "--type", "WHY"])
        assert rc == 1

    def test_cli_json_flag(self, tmp_path, capsys):
        """--json flag outputs valid JSON."""
        ep_file = tmp_path / "ep.json"
        ep_file.write_text(json.dumps([{"episodeId": "ep-001", "decisionType": "Demo",
                                        "outcome": {"code": "success"}, "degrade": {}}]))
        rc = self._run_cli(["iris", "query", str(ep_file), "--type", "STATUS", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "query_id" in parsed
        assert "status" in parsed

    def test_cli_invalid_type_exits(self, tmp_path):
        """Invalid query type causes exit code 2 (argparse choice validation)."""
        ep_file = tmp_path / "ep.json"
        ep_file.write_text(json.dumps([{"episodeId": "ep-001", "decisionType": "Demo",
                                        "outcome": {"code": "success"}, "degrade": {}}]))
        rc = self._run_cli(["iris", "query", str(ep_file), "--type", "BOGUS"])
        assert rc == 2
