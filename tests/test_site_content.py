"""Tests for generate_site_content.py script."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "data"


class TestGenerateSiteContent:

    def test_generate_creates_demo_json(self, output_dir):
        from generate_site_content import generate_demo_json

        output_dir.mkdir(parents=True, exist_ok=True)
        path = generate_demo_json(output_dir)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "baseline" in data
        assert "drift" in data

    def test_generate_creates_metrics_json(self, output_dir):
        from generate_site_content import generate_metrics_json

        output_dir.mkdir(parents=True, exist_ok=True)
        path = generate_metrics_json(output_dir)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "metrics" in data

    def test_demo_json_has_expected_keys(self, output_dir):
        from generate_site_content import generate_demo_json

        output_dir.mkdir(parents=True, exist_ok=True)
        path = generate_demo_json(output_dir)
        data = json.loads(path.read_text())
        baseline = data["baseline"]
        assert "overall_score" in baseline
        assert "grade" in baseline
        assert "dimensions" in baseline
