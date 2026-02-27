"""Tests for FEEDS CLI commands."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "src" / "core" / "fixtures" / "feeds"
REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "core.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT / "src"),
    )


class TestFeedsValidateCLI:
    def test_valid_fixture_exits_0(self):
        result = run_cli("feeds", "validate", str(FIXTURES_DIR / "ts_golden.json"))
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_valid_directory_exits_0(self):
        result = run_cli("feeds", "validate", str(FIXTURES_DIR))
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_invalid_event_exits_1(self, tmp_path):
        bad_event = {"eventId": "test", "topic": "invalid"}
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_event))
        result = run_cli("feeds", "validate", str(bad_file))
        assert result.returncode == 1
        assert "FAIL" in result.stdout

    def test_json_output(self):
        result = run_cli("feeds", "validate", "--json", str(FIXTURES_DIR / "ts_golden.json"))
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["valid"] is True
        assert len(data["results"]) == 1

    def test_json_output_invalid(self, tmp_path):
        bad_event = {"topic": "bad"}
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_event))
        result = run_cli("feeds", "validate", "--json", str(bad_file))
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["valid"] is False

    def test_missing_path_exits_1(self, tmp_path):
        result = run_cli("feeds", "validate", str(tmp_path / "nonexistent.json"))
        assert result.returncode == 1
