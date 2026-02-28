"""Tests for JRM CLI wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "fixtures" / "jrm"


class TestCLIWiring:
    def test_jrm_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "jrm", "--help"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2] / "src"),
        )
        assert result.returncode == 0
        assert "jrm" in result.stdout.lower()

    def test_jrm_adapters(self):
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "jrm", "adapters", "--json"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2] / "src"),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "suricata_eve" in data["adapters"]
        assert "snort_fastlog" in data["adapters"]
        assert "copilot_agent" in data["adapters"]

    def test_jrm_ingest_and_run(self, tmp_path):
        src_dir = Path(__file__).resolve().parents[2] / "src"
        norm_file = tmp_path / "normalized.ndjson"
        packet_dir = tmp_path / "packets"
        packet_dir.mkdir()

        # Ingest
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "jrm", "ingest",
             "--adapter", "suricata_eve",
             "--in", str(FIXTURES_DIR / "suricata_eve_sample.jsonl"),
             "--out", str(norm_file),
             "--env", "TEST",
             "--json"],
            capture_output=True, text=True,
            cwd=str(src_dir),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["events"] > 0

        # Run
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "jrm", "run",
             "--in", str(norm_file),
             "--env", "TEST",
             "--packet-out", str(packet_dir),
             "--json"],
            capture_output=True, text=True,
            cwd=str(src_dir),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["packetsBuilt"] >= 1

        # Validate produced packet
        packets = list(packet_dir.glob("*.zip"))
        assert len(packets) >= 1
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "jrm", "validate",
             str(packets[0]), "--json"],
            capture_output=True, text=True,
            cwd=str(src_dir),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["valid"] is True
