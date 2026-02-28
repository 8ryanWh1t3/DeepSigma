"""Tests for the AgentSession module and agent CLI commands."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.agent import AgentSession


SAMPLE_DECISION = {
    "action": "quarantine_account",
    "reason": "Suspicious activity detected",
    "actor": {"type": "agent", "id": "test-agent"},
    "targets": ["acc-12345"],
    "evidence": ["alert-789"],
    "confidence": 0.92,
}


# ── AgentSession unit tests ──────────────────────────────────────


class TestAgentSessionLogDecision:
    def test_log_returns_sealed_episode(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        assert ep["episodeId"].startswith("ep-test-agent-")
        assert "sealHash" in ep["seal"]
        assert ep["seal"]["sealHash"].startswith("sha256:")
        assert ep["sealedAt"]

    def test_log_sets_actor(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        assert ep["actor"] == {"type": "agent", "id": "test-agent"}

    def test_log_sets_action_targets(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        assert ep["actions"][0]["targetRefs"] == ["acc-12345"]

    def test_log_sets_evidence_refs(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        assert ep["context"]["evidenceRefs"] == ["alert-789"]

    def test_log_increments_counter(self):
        session = AgentSession("test-agent")
        ep1 = session.log_decision(SAMPLE_DECISION)
        ep2 = session.log_decision(SAMPLE_DECISION)
        assert ep1["episodeId"] != ep2["episodeId"]
        assert ep1["episodeId"] == "ep-test-agent-0001"
        assert ep2["episodeId"] == "ep-test-agent-0002"

    def test_log_accepts_full_episode(self, minimal_episode):
        session = AgentSession("test-agent")
        full = minimal_episode(episode_id="ep-custom")
        ep = session.log_decision(full)
        assert ep["episodeId"] == "ep-custom"

    def test_log_stores_confidence(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        assert ep["context"]["confidence"] == 0.92


class TestAgentSessionDrift:
    def test_no_drift_on_first_decision(self):
        session = AgentSession("test-agent")
        signals = session.detect_drift(SAMPLE_DECISION)
        assert signals == []

    def test_drift_on_outcome_change(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)

        modified = dict(SAMPLE_DECISION)
        modified["_outcome"] = "failure"  # won't trigger — need to use full episode

        # Use full episodes for outcome change detection
        session2 = AgentSession("test-agent-2")
        ep1 = session2.log_decision(SAMPLE_DECISION)
        ep1["outcome"]["code"] = "success"
        session2._episodes[-1] = ep1

        decision2 = dict(SAMPLE_DECISION)
        decision2["action"] = "different_action"
        signals = session2.detect_drift(decision2)
        assert len(signals) >= 1

    def test_drift_on_confidence_shift(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)

        low_conf = dict(SAMPLE_DECISION)
        low_conf["confidence"] = 0.3  # delta = 0.62
        signals = session.detect_drift(low_conf)
        # Should detect confidence drift
        confidence_drifts = [s for s in signals if s["driftType"] == "freshness"]
        assert len(confidence_drifts) >= 1
        assert confidence_drifts[0]["severity"] in ("yellow", "red")


class TestAgentSessionAudit:
    def test_audit_returns_report(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        report = session.audit()
        assert "passed" in report
        assert "summary" in report

    def test_audit_passed_on_clean_data(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        report = session.audit()
        assert report["passed"] is True


class TestAgentSessionScore:
    def test_score_returns_report(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        report = session.score()
        assert "overall_score" in report
        assert "grade" in report
        assert 0 <= report["overall_score"] <= 100

    def test_score_grade_valid(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        report = session.score()
        assert report["grade"] in ("A", "B", "C", "D", "F")


class TestAgentSessionProve:
    def test_prove_found(self):
        session = AgentSession("test-agent")
        ep = session.log_decision(SAMPLE_DECISION)
        proof = session.prove(ep["episodeId"])
        assert proof["episodeId"] == ep["episodeId"]
        assert "seal" in proof
        assert proof["memory_graph_nodes"] >= 1

    def test_prove_not_found(self):
        session = AgentSession("test-agent")
        proof = session.prove("nonexistent")
        assert "error" in proof


class TestAgentSessionExport:
    def test_export_json(self):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        raw = session.export()
        data = json.loads(raw)
        assert data["agent_id"] == "test-agent"
        assert data["episode_count"] == 1
        assert len(data["episodes"]) == 1


class TestAgentSessionAuthority:
    def test_grant_authority_returns_entry(self, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        result = session.grant_authority({
            "claims_blessed": ["CLAIM-A"],
            "scope": "test",
        })
        assert "entry_id" in result
        assert result["entry_hash"].startswith("sha256:")

    def test_grant_authority_no_ledger(self):
        session = AgentSession("test-agent")
        result = session.grant_authority({"claims_blessed": ["CLAIM-A"]})
        assert "error" in result

    def test_verify_authority_valid(self, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        session.grant_authority({"claims_blessed": ["CLAIM-A"]})
        result = session.verify_authority()
        assert result["chain_valid"] is True
        assert result["entry_count"] == 1

    def test_prove_claim_authority_found(self, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        session.grant_authority({"claims_blessed": ["CLAIM-A"]})
        proof = session.prove_claim_authority("CLAIM-A")
        assert proof is not None
        assert proof["claim_id"] == "CLAIM-A"

    def test_prove_claim_authority_not_found(self, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        proof = session.prove_claim_authority("NONEXISTENT")
        assert proof is None


class TestAgentSessionClaims:
    def test_submit_clean_claim(self, minimal_claim):
        session = AgentSession("test-agent")
        session.log_decision(SAMPLE_DECISION)
        result = session.submit_claims([minimal_claim()])
        assert result["submitted"] == 1
        assert result["accepted"] == 1

    def test_submit_collects_drift(self, minimal_claim, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        # No authority granted -> unauthorized drift
        result = session.submit_claims([minimal_claim(claim_id="UNAUTH")])
        assert result["rejected"] == 1
        assert len(session._drift_events) >= 1

    def test_submit_with_authority(self, minimal_claim, tmp_path):
        session = AgentSession(
            "test-agent",
            authority_ledger=tmp_path / "ledger.json",
        )
        session.grant_authority({"claims_blessed": ["AUTH-CLAIM"]})
        result = session.submit_claims([minimal_claim(claim_id="AUTH-CLAIM")])
        assert result["accepted"] == 1
        assert result["rejected"] == 0

    def test_submit_result_shape(self, minimal_claim):
        session = AgentSession("test-agent")
        result = session.submit_claims([minimal_claim()])
        assert "submitted" in result
        assert "accepted" in result
        assert "rejected" in result
        assert "drift_signals_emitted" in result
        assert "results" in result


class TestAgentSessionStorage:
    def test_persist_and_reload(self, tmp_path):
        session1 = AgentSession("test-agent", storage_dir=tmp_path / "agent")
        ep = session1.log_decision(SAMPLE_DECISION)

        # Reload from disk
        session2 = AgentSession("test-agent", storage_dir=tmp_path / "agent")
        assert len(session2._episodes) == 1
        assert session2._episodes[0]["episodeId"] == ep["episodeId"]


# ── CLI integration tests ────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "src" / "core" / "fixtures" / "agent_sample_decision.json"


class TestAgentCLI:
    def test_agent_log(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "log",
             str(FIXTURE), "--session-dir", str(tmp_path), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "episodeId" in data
        assert "seal" in data

    def test_agent_score(self, tmp_path):
        # First log a decision
        subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "log",
             str(FIXTURE), "--session-dir", str(tmp_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        # Then score
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "score",
             "--session-dir", str(tmp_path), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "overall_score" in data
        assert "grade" in data

    def test_agent_audit(self, tmp_path):
        subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "log",
             str(FIXTURE), "--session-dir", str(tmp_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "audit",
             "--session-dir", str(tmp_path), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "passed" in data

    def test_demo_no_args(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "demo"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "BASELINE" in result.stdout
        assert "DRIFT" in result.stdout
        assert "PATCH" in result.stdout

    def test_demo_json(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "demo", "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "baseline" in data
        assert "drift" in data
        assert "patch" in data
        assert data["baseline"]["grade"] == "A"


AUTHORITY_FIXTURE = REPO_ROOT / "src" / "core" / "fixtures" / "authority_grant_sample.json"


class TestAuthorityCLI:
    def test_authority_grant(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "grant",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["entry_type"] == "grant"
        assert "CLAIM-2026-0001" in data["claims_blessed"]

    def test_authority_verify(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        # First grant
        subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "grant",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        # Then verify
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "verify",
             "--ledger", str(ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["chain_valid"] is True

    def test_authority_prove(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "grant",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "prove",
             "CLAIM-2026-0001", "--ledger", str(ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["claim_id"] == "CLAIM-2026-0001"


CLAIM_FIXTURE = REPO_ROOT / "src" / "core" / "fixtures" / "claim_sample.json"


class TestClaimCLI:
    def test_claim_validate(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "feeds", "claim", "validate",
             str(CLAIM_FIXTURE), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0  # yellow warnings exit 0, only red exits 1
        data = json.loads(result.stdout)
        assert "valid" in data
        assert "results" in data
        # If issues exist they must all be yellow (non-blocking)
        for r in data["results"]:
            for issue in r.get("issues", []):
                assert issue["severity"] != "red"

    def test_claim_submit(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "feeds", "claim", "submit",
             str(CLAIM_FIXTURE), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["submitted"] == 1
        assert data["accepted"] == 1


class TestAuthorityCLIExtended:
    def test_authority_revoke(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        # Grant first
        subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "grant",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        # Revoke using same fixture (reuses fields)
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "revoke",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["entry_type"] == "revocation"

    def test_authority_list(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "grant",
             str(AUTHORITY_FIXTURE), "--ledger", str(ledger)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "authority", "list",
             "--ledger", str(ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["entry_type"] == "grant"


class TestMetricsCLI:
    def test_metrics_json(self, tmp_path):
        # Write a minimal episode file
        episode = {
            "episodeId": "ep-test-1",
            "decisionType": "test",
            "outcome": {"code": "success"},
            "startedAt": "2026-01-01T00:00:00Z",
            "endedAt": "2026-01-01T00:01:00Z",
        }
        ep_file = tmp_path / "episodes.json"
        ep_file.write_text(json.dumps([episode]))
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "metrics",
             str(ep_file), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "metrics" in data
        assert len(data["metrics"]) >= 1

    def test_agent_metrics_json(self, tmp_path):
        session_dir = tmp_path / "session"
        # Log a decision via agent CLI first
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "log",
             str(FIXTURE), "--session-dir", str(session_dir), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        # Now collect metrics
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "agent", "metrics",
             "--session-dir", str(session_dir), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "metrics" in data
