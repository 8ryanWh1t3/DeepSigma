"""Unit tests for coherence_ops.rs — Reflection Session (Reality Snapshot)."""
import json
import pytest
from coherence_ops.rs import ReflectionSession, ReflectionSummary, Divergence


def _ep(episode_id="ep-1", outcome="success", degrade="none", verify="pass"):
    """Minimal episode for RS tests."""
    return {
        "episodeId": episode_id,
        "decisionType": "AccountQuarantine",
        "outcome": {"code": outcome},
        "degrade": {"step": degrade},
        "verification": {"result": verify},
    }


class TestReflectionSession:
    """ReflectionSession produces valid summaries from TTL/freshness data."""

    def test_basic_summary(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_ep(), _ep(episode_id="ep-2")])
        summary = rs.summarise()
        assert isinstance(summary, ReflectionSummary)
        assert summary.episode_count == 2
        assert summary.session_id == "rs-001"

    def test_outcome_distribution(self):
        rs = ReflectionSession("rs-002")
        rs.ingest([
            _ep(outcome="success"),
            _ep(outcome="success"),
            _ep(outcome="fail"),
        ])
        summary = rs.summarise()
        assert summary.outcome_distribution["success"] == 2
        assert summary.outcome_distribution["fail"] == 1

    def test_degrade_distribution(self):
        rs = ReflectionSession("rs-003")
        rs.ingest([
            _ep(degrade="none"),
            _ep(degrade="fallback_cache"),
            _ep(degrade="fallback_cache"),
        ])
        summary = rs.summarise()
        assert summary.degrade_distribution["fallback_cache"] == 2
        assert summary.degrade_distribution["none"] == 1

    def test_verification_pass_rate_perfect(self):
        rs = ReflectionSession("rs-004")
        rs.ingest([_ep(verify="pass"), _ep(verify="pass")])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 1.0

    def test_verification_pass_rate_mixed(self):
        rs = ReflectionSession("rs-005")
        rs.ingest([_ep(verify="pass"), _ep(verify="fail")])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 0.5

    def test_verification_all_na(self):
        rs = ReflectionSession("rs-006")
        rs.ingest([_ep(verify="na")])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 1.0

    def test_divergence_verify_fail_outcome_success(self):
        rs = ReflectionSession("rs-007")
        rs.ingest([_ep(verify="fail", outcome="success")])
        summary = rs.summarise()
        critical = [d for d in summary.divergences if d.severity == "critical"]
        assert len(critical) == 1
        assert critical[0].field == "verification_vs_outcome"

    def test_divergence_degrade_with_success(self):
        rs = ReflectionSession("rs-008")
        rs.ingest([_ep(degrade="fallback_cache", outcome="success")])
        summary = rs.summarise()
        info_divs = [d for d in summary.divergences if d.severity == "info"]
        assert len(info_divs) >= 1

    def test_empty_session(self):
        rs = ReflectionSession("rs-009")
        rs.ingest([])
        summary = rs.summarise()
        assert summary.episode_count == 0
        assert "No episodes" in summary.takeaways[0]

    def test_takeaway_high_failure(self):
        rs = ReflectionSession("rs-010")
        eps = [_ep(outcome="fail")] * 5 + [_ep(outcome="success")] * 5
        rs.ingest(eps)
        summary = rs.summarise()
        assert any("failure rate" in t.lower() for t in summary.takeaways)

    def test_to_json_valid(self):
        rs = ReflectionSession("rs-011")
        rs.ingest([_ep()])
        raw = rs.to_json()
        data = json.loads(raw)
        assert data["session_id"] == "rs-011"
        assert data["episode_count"] == 1

    def test_ingest_multiple_batches(self):
        rs = ReflectionSession("rs-012")
        rs.ingest([_ep(episode_id="ep-1")])
        rs.ingest([_ep(episode_id="ep-2")])
        summary = rs.summarise()
        assert summary.episode_count == 2
