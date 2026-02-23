"""Tests for demos/excel_first/ — Excel-first Money Demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

pytestmark = pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")

EXPECTED_FILES = [
    "workbook.xlsx",
    "run_record.json",
    "drift_signal.json",
    "patch_stub.json",
    "coherence_delta.txt",
]


@pytest.fixture(scope="module")
def demo_output(tmp_path_factory):
    """Run demo once for all tests in this module."""
    out = tmp_path_factory.mktemp("excel_demo")
    from demos.excel_first.pipeline import run_demo
    result = run_demo(str(out))
    return out, result


class TestDemoArtifacts:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_artifact_exists(self, demo_output, filename):
        out, _ = demo_output
        assert (out / filename).exists(), f"Missing artifact: {filename}"


class TestCoherenceDelta:
    def test_contains_before_score(self, demo_output):
        out, _ = demo_output
        text = (out / "coherence_delta.txt").read_text()
        assert "before_score" in text

    def test_contains_after_score(self, demo_output):
        out, _ = demo_output
        text = (out / "coherence_delta.txt").read_text()
        assert "after_score" in text

    def test_after_greater_than_before(self, demo_output):
        _, result = demo_output
        assert result["after_score"] > result["before_score"]


class TestDriftSignal:
    def test_drift_detected_true(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "drift_signal.json").read_text())
        assert data["drift_detected"] is True

    def test_drift_type_is_freshness(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "drift_signal.json").read_text())
        assert data["drift_type"] == "freshness"

    def test_drift_has_severity(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "drift_signal.json").read_text())
        assert data["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class TestPatchStub:
    def test_patch_has_id(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "patch_stub.json").read_text())
        assert data["patch_id"] is not None

    def test_patch_references_drift(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "patch_stub.json").read_text())
        assert "drift_ref" in data
        assert data["drift_ref"].startswith("DRIFT-")

    def test_patch_has_action(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "patch_stub.json").read_text())
        assert len(data["action"]) > 0


class TestRunRecord:
    def test_has_scenario_id(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "run_record.json").read_text())
        assert "scenario_id" in data

    def test_has_assumption_ref(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "run_record.json").read_text())
        assert data["assumption_id"] == "ASM-005"

    def test_ttl_expired(self, demo_output):
        out, _ = demo_output
        data = json.loads((out / "run_record.json").read_text())
        assert data["ttl_expired"] is True
