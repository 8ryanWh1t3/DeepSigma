"""Tests for the Trust Scorecard generator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from demos.golden_path.config import GoldenPathConfig
from demos.golden_path.pipeline import GoldenPathPipeline

FIXTURE_DIR = str(Path(__file__).parent.parent / "demos" / "golden_path" / "fixtures" / "sharepoint_small")


def _run_golden_path(output_dir: str) -> dict:
    """Run golden path pipeline and return summary."""
    config = GoldenPathConfig(
        source="sharepoint",
        fixture_path=FIXTURE_DIR,
        output_dir=output_dir,
    )
    GoldenPathPipeline(config).run()
    return json.loads((Path(output_dir) / "summary.json").read_text())


# ── Scorecard generation tests ───────────────────────────────────────────────


class TestTrustScorecard:
    def _generate(self, tmp_path):
        from tools.trust_scorecard import generate_scorecard
        gp_out = str(tmp_path / "gp_out")
        _run_golden_path(gp_out)
        return generate_scorecard(gp_out)

    def test_scorecard_version(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["scorecard_version"] == "1.0"

    def test_has_timestamp(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["timestamp"]

    def test_has_source_dir(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["source_dir"]

    def test_metrics_keys(self, tmp_path):
        sc = self._generate(tmp_path)
        m = sc["metrics"]
        required = [
            "iris_why_latency_ms", "drift_detect_latency_ms", "patch_latency_ms",
            "connector_ingest_records_per_sec", "schema_validation_failures",
            "total_elapsed_ms", "steps_completed", "steps_total",
            "all_steps_passed", "drift_events_detected", "patch_applied",
            "iris_queries_resolved", "baseline_score", "baseline_grade",
            "patched_score", "patched_grade", "coverage_pct",
        ]
        for key in required:
            assert key in m, f"Missing metric: {key}"

    def test_slo_checks_keys(self, tmp_path):
        sc = self._generate(tmp_path)
        slo = sc["slo_checks"]
        for key in ("iris_why_latency_ok", "all_steps_passed", "schema_clean", "score_positive"):
            assert key in slo, f"Missing SLO check: {key}"

    def test_all_steps_passed(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["steps_completed"] == 7
        assert sc["metrics"]["all_steps_passed"] is True

    def test_scores_positive(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["baseline_score"] > 0
        assert sc["metrics"]["patched_score"] > 0

    def test_iris_resolved(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["iris_queries_resolved"] == 3

    def test_drift_detected(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["drift_events_detected"] > 0

    def test_patch_applied(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["patch_applied"] is True

    def test_schema_clean(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["schema_validation_failures"] == 0

    def test_slo_all_pass(self, tmp_path):
        sc = self._generate(tmp_path)
        assert all(sc["slo_checks"].values())

    def test_numeric_metrics(self, tmp_path):
        sc = self._generate(tmp_path)
        m = sc["metrics"]
        assert isinstance(m["iris_why_latency_ms"], (int, float))
        assert isinstance(m["total_elapsed_ms"], (int, float))
        assert isinstance(m["connector_ingest_records_per_sec"], (int, float))
        assert isinstance(m["steps_completed"], int)
        assert isinstance(m["steps_total"], int)

    def test_coverage_default_null(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["coverage_pct"] is None

    def test_coverage_passthrough(self, tmp_path):
        from tools.trust_scorecard import generate_scorecard
        gp_out = str(tmp_path / "gp_out")
        _run_golden_path(gp_out)
        sc = generate_scorecard(gp_out, coverage_pct=85.3)
        assert sc["metrics"]["coverage_pct"] == 85.3

    def test_grades_are_letters(self, tmp_path):
        sc = self._generate(tmp_path)
        assert sc["metrics"]["baseline_grade"] in ("A", "B", "C", "D", "F")
        assert sc["metrics"]["patched_grade"] in ("A", "B", "C", "D", "F")


# ── CLI tests ────────────────────────────────────────────────────────────────


class TestTrustScorecardCLI:
    def test_cli_writes_file(self, tmp_path):
        from tools.trust_scorecard import main
        gp_out = str(tmp_path / "gp_out")
        _run_golden_path(gp_out)
        out_path = str(tmp_path / "scorecard.json")
        rc = main(["--input", gp_out, "--output", out_path])
        assert rc == 0
        assert Path(out_path).exists()
        data = json.loads(Path(out_path).read_text())
        assert data["scorecard_version"] == "1.0"

    def test_cli_missing_input(self, tmp_path):
        from tools.trust_scorecard import main
        rc = main(["--input", str(tmp_path / "nonexistent"), "--output", "/dev/null"])
        assert rc == 1
