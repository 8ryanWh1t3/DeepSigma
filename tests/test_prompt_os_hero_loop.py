"""Tests for the Prompt OS Drift → Patch hero loop."""
from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Adjust import path so we can import from src/tools/prompt_os
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "prompt_os"))

import drift_to_patch_demo as hero  # noqa: E402


# ── Sample CSV content ───────────────────────────────────────────
DECISION_HEADER = (
    "DecisionID,Title,Category,Owner,Status,Confidence_pct,"
    "BlastRadius_1to5,Reversibility_1to5,CostOfDelay,CompressionRisk,"
    "Evidence,CounterEvidence,Assumptions,DateLogged,ReviewDate,PriorityScore,Notes"
)

# DEC-RED triggers Rule 1: BlastRadius>=4, Status=Active, Confidence<70
ROW_RED = (
    "DEC-RED,High-blast low-conf decision,Tech,Tester,Active,41,"
    "5,2,Medium,High,Evidence,Counter,Assumption,2026-01-01,2026-04-01,8.05,note"
)

# DEC-SAFE: no drift — high confidence
ROW_SAFE = (
    "DEC-SAFE,Safe decision,Tech,Tester,Active,90,"
    "1,1,Low,Low,Evidence,Counter,Assumption,2026-01-01,2026-04-01,2.0,note"
)

# DEC-YELLOW triggers Rule 2: PriorityScore>=12, Status=Active
ROW_YELLOW = (
    "DEC-YEL,Very high priority,Ops,Tester,Active,80,"
    "3,2,High,High,Evidence,Counter,Assumption,2026-01-01,2026-04-01,14.0,note"
)

PATCH_HEADER = (
    "PatchID,TriggerType,TriggerID,Description,Severity_GYR,"
    "Status,Owner,DateCreated,DateResolved,Resolution,Notes"
)

LLM_HEADER = (
    "RunID,SessionDate,Model,TopActions,TopRisks,SuggestedUpdates,"
    "SealHash,SummaryConfidence_pct,NextReviewDate,Operator,Notes"
)
LLM_ROW = (
    "RUN-001,2026-01-02,test-model,Action A,Risk X,Update X,"
    "sha256:abcd,70,2026-01-09,Tester,note"
)


class HeroLoopTestBase(unittest.TestCase):
    """Base class that sets up a temp workspace with sample CSVs."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = Path(self.tmpdir) / "data"
        self.data_dir.mkdir()
        self.out_dir = Path(self.tmpdir) / "sealed"
        self.out_dir.mkdir()

        # Write patch_log (header only)
        (self.data_dir / "patch_log.csv").write_text(PATCH_HEADER + "\n")

        # Write llm_output
        (self.data_dir / "llm_output.csv").write_text(
            LLM_HEADER + "\n" + LLM_ROW + "\n"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_decisions(self, *rows: str) -> None:
        content = DECISION_HEADER + "\n" + "\n".join(rows) + "\n"
        (self.data_dir / "decision_log.csv").write_text(content)


class TestRedDrift(HeroLoopTestBase):
    """Test that a RED drift condition creates a patch + telemetry + sealed JSON."""

    def test_red_drift_creates_artifacts(self) -> None:
        self._write_decisions(ROW_RED)

        # Monkey-patch defaults so script uses our temp dirs
        old_data = hero.DEFAULT_DATA_DIR
        old_out = hero.DEFAULT_OUT_DIR
        old_tel = hero.DEFAULT_TELEMETRY_DIR
        hero.DEFAULT_DATA_DIR = self.data_dir
        hero.DEFAULT_OUT_DIR = self.out_dir
        hero.DEFAULT_TELEMETRY_DIR = Path(self.tmpdir) / "telemetry"
        try:
            rc = hero.main.__wrapped__() if hasattr(hero.main, "__wrapped__") else None
            # Run via sys.argv simulation
            sys.argv = [
                "drift_to_patch_demo.py",
                "--run-id", "RUN-TEST",
                "--user", "Tester",
                "--data-dir", str(self.data_dir),
                "--out-dir", str(self.out_dir),
            ]
            rc = hero.main()
        finally:
            hero.DEFAULT_DATA_DIR = old_data
            hero.DEFAULT_OUT_DIR = old_out
            hero.DEFAULT_TELEMETRY_DIR = old_tel

        self.assertEqual(rc, 0)

        # 1) Sealed JSON was created
        json_files = list(self.out_dir.glob("RUN-TEST_*.json"))
        self.assertEqual(len(json_files), 1, "Expected exactly one sealed JSON")
        sealed = json.loads(json_files[0].read_text())
        self.assertEqual(sealed["meta"]["run_id"], "RUN-TEST")
        self.assertTrue(sealed["drift"]["detected"])
        self.assertEqual(sealed["drift"]["severity"], "RED")
        self.assertEqual(sealed["drift"]["decision_id"], "DEC-RED")
        self.assertTrue(sealed["hash"].startswith("sha256:"))

        # 2) Patch row was appended
        patch_rows = hero.read_csv(self.data_dir / "patch_log.csv")
        new_patches = [r for r in patch_rows if r["TriggerID"] == "DEC-RED"]
        self.assertGreaterEqual(len(new_patches), 1)
        self.assertEqual(new_patches[0]["Severity_GYR"], "RED")
        self.assertTrue(new_patches[0]["PatchID"].startswith("PX-"))

        # 3) Telemetry row was emitted
        tel_dir = Path(self.tmpdir) / "telemetry"
        tel_path = tel_dir / "telemetry_events.csv"
        self.assertTrue(tel_path.exists(), "Telemetry file should exist")
        tel_rows = hero.read_csv(tel_path)
        self.assertGreaterEqual(len(tel_rows), 1)
        self.assertEqual(tel_rows[0]["Event"], "drift_flag")
        self.assertEqual(tel_rows[0]["Severity"], "RED")


class TestGreenNoDrift(HeroLoopTestBase):
    """Test that a GREEN (no drift) run still creates a sealed JSON but no patch."""

    def test_green_no_patch(self) -> None:
        self._write_decisions(ROW_SAFE)

        old_tel = hero.DEFAULT_TELEMETRY_DIR
        hero.DEFAULT_TELEMETRY_DIR = Path(self.tmpdir) / "telemetry"
        try:
            sys.argv = [
                "drift_to_patch_demo.py",
                "--run-id", "RUN-GREEN",
                "--user", "Tester",
                "--data-dir", str(self.data_dir),
                "--out-dir", str(self.out_dir),
            ]
            rc = hero.main()
        finally:
            hero.DEFAULT_TELEMETRY_DIR = old_tel

        self.assertEqual(rc, 0)

        # Sealed JSON exists
        json_files = list(self.out_dir.glob("RUN-GREEN_*.json"))
        self.assertEqual(len(json_files), 1)
        sealed = json.loads(json_files[0].read_text())
        self.assertFalse(sealed["drift"]["detected"])
        self.assertEqual(sealed["drift"]["severity"], "GREEN")

        # No new patch rows (only header)
        patch_rows = hero.read_csv(self.data_dir / "patch_log.csv")
        self.assertEqual(len(patch_rows), 0)


class TestYellowDrift(HeroLoopTestBase):
    """Test that Rule 2 (YELLOW) triggers when Rule 1 does not."""

    def test_yellow_drift(self) -> None:
        self._write_decisions(ROW_SAFE, ROW_YELLOW)

        old_tel = hero.DEFAULT_TELEMETRY_DIR
        hero.DEFAULT_TELEMETRY_DIR = Path(self.tmpdir) / "telemetry"
        try:
            sys.argv = [
                "drift_to_patch_demo.py",
                "--run-id", "RUN-YEL",
                "--user", "Tester",
                "--data-dir", str(self.data_dir),
                "--out-dir", str(self.out_dir),
            ]
            rc = hero.main()
        finally:
            hero.DEFAULT_TELEMETRY_DIR = old_tel

        self.assertEqual(rc, 0)

        json_files = list(self.out_dir.glob("RUN-YEL_*.json"))
        self.assertEqual(len(json_files), 1)
        sealed = json.loads(json_files[0].read_text())
        self.assertTrue(sealed["drift"]["detected"])
        self.assertEqual(sealed["drift"]["severity"], "YELLOW")

        patch_rows = hero.read_csv(self.data_dir / "patch_log.csv")
        new_patches = [r for r in patch_rows if r["TriggerID"] == "DEC-YEL"]
        self.assertGreaterEqual(len(new_patches), 1)
        self.assertEqual(new_patches[0]["Severity_GYR"], "YELLOW")


class TestMissingFile(HeroLoopTestBase):
    """Test that missing required files produce exit code 2."""

    def test_missing_decision_log(self) -> None:
        # Don't write decision_log.csv
        old_tel = hero.DEFAULT_TELEMETRY_DIR
        hero.DEFAULT_TELEMETRY_DIR = Path(self.tmpdir) / "telemetry"
        try:
            sys.argv = [
                "drift_to_patch_demo.py",
                "--data-dir", str(self.data_dir),
                "--out-dir", str(self.out_dir),
            ]
            rc = hero.main()
        finally:
            hero.DEFAULT_TELEMETRY_DIR = old_tel

        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
