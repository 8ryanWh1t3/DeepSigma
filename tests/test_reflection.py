"""Tests for core.reflection — reflection session and learning summaries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.reflection import Divergence, ReflectionSession, ReflectionSummary  # noqa: E402


def _make_episode(
    episode_id="ep-001",
    outcome="success",
    degrade="none",
    verify="pass",
):
    return {
        "episodeId": episode_id,
        "outcome": {"code": outcome},
        "degrade": {"step": degrade},
        "verification": {"result": verify},
    }


class TestDivergence:
    def test_fields(self):
        d = Divergence(
            episode_id="ep-1",
            field="test_field",
            expected="expected",
            actual="actual",
            severity="critical",
        )
        assert d.episode_id == "ep-1"
        assert d.severity == "critical"

    def test_default_severity(self):
        d = Divergence(episode_id="ep-1", field="f", expected="e", actual="a")
        assert d.severity == "info"


class TestReflectionSession:
    def test_ingest_single(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode()])
        summary = rs.summarise()
        assert summary.episode_count == 1

    def test_ingest_multiple(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode(episode_id="ep-1"), _make_episode(episode_id="ep-2")])
        summary = rs.summarise()
        assert summary.episode_count == 2

    def test_ingest_batch(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode(episode_id="ep-1")])
        rs.ingest([_make_episode(episode_id="ep-2")])
        summary = rs.summarise()
        assert summary.episode_count == 2

    def test_outcome_distribution(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([
            _make_episode(outcome="success"),
            _make_episode(outcome="success"),
            _make_episode(outcome="fail"),
        ])
        summary = rs.summarise()
        assert summary.outcome_distribution["success"] == 2
        assert summary.outcome_distribution["fail"] == 1

    def test_degrade_distribution(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([
            _make_episode(degrade="none"),
            _make_episode(degrade="skip_verify"),
            _make_episode(degrade="skip_verify"),
        ])
        summary = rs.summarise()
        assert summary.degrade_distribution["none"] == 1
        assert summary.degrade_distribution["skip_verify"] == 2

    def test_verification_pass_rate_all_pass(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode(verify="pass"), _make_episode(verify="pass")])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 1.0

    def test_verification_pass_rate_mixed(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([
            _make_episode(verify="pass"),
            _make_episode(verify="fail"),
        ])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 0.5

    def test_verification_na_excluded(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([
            _make_episode(verify="pass"),
            _make_episode(verify="na"),
        ])
        summary = rs.summarise()
        assert summary.verification_pass_rate == 1.0

    def test_divergence_verify_fail_success(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode(outcome="success", verify="fail")])
        summary = rs.summarise()
        assert len(summary.divergences) >= 1
        critical = [d for d in summary.divergences if d.severity == "critical"]
        assert len(critical) == 1

    def test_divergence_degrade_with_success(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode(outcome="success", degrade="skip_verify")])
        summary = rs.summarise()
        info_divs = [d for d in summary.divergences if d.severity == "info"]
        assert len(info_divs) == 1

    def test_no_divergence_clean(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode()])
        summary = rs.summarise()
        # No divergences for a clean pass
        critical = [d for d in summary.divergences if d.severity == "critical"]
        assert len(critical) == 0

    def test_takeaway_high_failure(self):
        rs = ReflectionSession("rs-001")
        episodes = [_make_episode(outcome="fail") for _ in range(5)]
        rs.ingest(episodes)
        summary = rs.summarise()
        assert any("failure rate" in t.lower() for t in summary.takeaways)

    def test_takeaway_low_verify_rate(self):
        rs = ReflectionSession("rs-001")
        episodes = [_make_episode(verify="fail") for _ in range(5)]
        rs.ingest(episodes)
        summary = rs.summarise()
        assert any("verification" in t.lower() for t in summary.takeaways)

    def test_takeaway_normal(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode()])
        summary = rs.summarise()
        assert any("normal" in t.lower() for t in summary.takeaways)

    def test_to_json_parseable(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode()])
        j = rs.to_json()
        data = json.loads(j)
        assert data["session_id"] == "rs-001"
        assert data["episode_count"] == 1

    def test_session_id_preserved(self):
        rs = ReflectionSession("my-session")
        rs.ingest([_make_episode()])
        summary = rs.summarise()
        assert summary.session_id == "my-session"

    def test_created_at_iso(self):
        rs = ReflectionSession("rs-001")
        rs.ingest([_make_episode()])
        summary = rs.summarise()
        assert "T" in summary.created_at

    def test_empty_session(self):
        rs = ReflectionSession("rs-001")
        summary = rs.summarise()
        assert summary.episode_count == 0
        assert summary.verification_pass_rate == 1.0
        assert "No episodes" in summary.takeaways[0]
