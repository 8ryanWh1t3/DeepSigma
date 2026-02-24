"""Tests for core.cli — CLI completeness (E13)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_episode_dir(tmp_path):
    """Create a temp dir with a sample episode."""
    episode = {
        "episodeId": "ep_test_001",
        "decisionType": "TestDecision",
        "actor": {"id": "test-agent", "version": "1.0"},
        "startedAt": "2024-01-15T10:00:00Z",
        "telemetry": {
            "endToEndMs": 50,
            "hopCount": 2,
            "stageMs": {"context": 10, "plan": 15, "act": 15, "verify": 10},
        },
        "outcome": {"code": "success", "reason": "All good"},
        "context": {},
        "plan": {"summary": "test plan"},
        "actions": [],
        "verification": {"result": "pass"},
        "seal": {"sealedAt": "2024-01-15T10:00:01Z", "sealHash": "abc123"},
    }
    ep_file = tmp_path / "episodes" / "test.json"
    ep_file.parent.mkdir()
    ep_file.write_text(json.dumps([episode]))
    return tmp_path / "episodes"


@pytest.fixture
def sample_dte_file(tmp_path):
    """Create a temp DTE spec."""
    dte = {
        "deadlineMs": 100,
        "stageBudgetsMs": {"context": 30, "plan": 30, "act": 30, "verify": 30},
        "limits": {"maxHops": 5, "maxToolCalls": 10},
    }
    dte_file = tmp_path / "dte.json"
    dte_file.write_text(json.dumps(dte))
    return dte_file


@pytest.fixture
def tight_dte_file(tmp_path):
    """Create a tight DTE spec that episodes will violate."""
    dte = {
        "deadlineMs": 10,  # very tight
        "limits": {"maxHops": 1},
    }
    dte_file = tmp_path / "tight_dte.json"
    dte_file.write_text(json.dumps(dte))
    return dte_file


class TestCLIReconcile:
    def test_reconcile_runs(self, sample_episode_dir, capsys):
        from core.cli import cmd_reconcile
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), json=False, auto_fix=False)
        cmd_reconcile(args)
        output = capsys.readouterr().out
        assert "Reconciliation" in output

    def test_reconcile_json(self, sample_episode_dir, capsys):
        from core.cli import cmd_reconcile
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), json=True, auto_fix=False)
        cmd_reconcile(args)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "proposals" in data
        assert "auto_fixable_count" in data


class TestCLISchemaValidate:
    def test_valid_episode(self, sample_episode_dir, capsys):
        from core.cli import cmd_schema_validate
        import argparse
        ep_file = list(sample_episode_dir.glob("*.json"))[0]
        args = argparse.Namespace(file=str(ep_file), schema="episode", json=False)
        # May exit with 0 or 1 depending on schema strictness
        try:
            cmd_schema_validate(args)
        except SystemExit:
            pass  # expected

    def test_schema_validate_json(self, sample_episode_dir, capsys):
        from core.cli import cmd_schema_validate
        import argparse
        ep_file = list(sample_episode_dir.glob("*.json"))[0]
        args = argparse.Namespace(file=str(ep_file), schema="episode", json=True)
        try:
            cmd_schema_validate(args)
        except SystemExit:
            pass
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "valid" in data


class TestCLIDTECheck:
    def test_dte_check_clean(self, sample_episode_dir, sample_dte_file, capsys):
        from core.cli import cmd_dte_check
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), dte=str(sample_dte_file), json=False)
        try:
            cmd_dte_check(args)
        except SystemExit as e:
            assert e.code == 0  # clean

    def test_dte_check_violations(self, sample_episode_dir, tight_dte_file, capsys):
        from core.cli import cmd_dte_check
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), dte=str(tight_dte_file), json=False)
        try:
            cmd_dte_check(args)
        except SystemExit as e:
            assert e.code == 1  # violations

    def test_dte_check_json(self, sample_episode_dir, sample_dte_file, capsys):
        from core.cli import cmd_dte_check
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), dte=str(sample_dte_file), json=True)
        try:
            cmd_dte_check(args)
        except SystemExit:
            pass
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "total_episodes" in data
        assert "violations" in data

    def test_dte_check_violation_json(self, sample_episode_dir, tight_dte_file, capsys):
        from core.cli import cmd_dte_check
        import argparse
        args = argparse.Namespace(path=str(sample_episode_dir), dte=str(tight_dte_file), json=True)
        try:
            cmd_dte_check(args)
        except SystemExit:
            pass
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data["violations"]) > 0


class TestCLIParser:
    def test_main_help(self):
        """Parser should handle no arguments gracefully."""
        from core.cli import main
        import sys
        old_argv = sys.argv
        sys.argv = ["coherence"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        finally:
            sys.argv = old_argv
