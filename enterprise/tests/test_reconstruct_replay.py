"""Tests for the reconstruct seal + replay pipeline."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

import seal_bundle  # noqa: E402
import replay_sealed_run as replay  # noqa: E402

FIXED_CLOCK = "2026-02-21T00:00:00Z"

# ── Sample data ──────────────────────────────────────────────────
DECISION_HEADER = (
    "DecisionID,Title,Category,Owner,Status,Confidence_pct,"
    "BlastRadius_1to5,Reversibility_1to5,CostOfDelay,CompressionRisk,"
    "Evidence,CounterEvidence,Assumptions,DateLogged,ReviewDate,PriorityScore,Notes"
)
DECISION_ROW = (
    "DEC-TEST,Test decision,Tech,Tester,Active,75,"
    "3,2,Medium,Low,Evidence,Counter,Assumption,2026-01-01,2026-04-01,6.0,note"
)


class ReconstructTestBase(unittest.TestCase):
    """Base class that sets up a temp workspace with sample data."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = Path(self.tmpdir) / "artifacts" / "sample_data" / "data"
        self.data_dir.mkdir(parents=True)
        self.out_dir = Path(self.tmpdir) / "sealed"
        self.out_dir.mkdir()
        self.prompts_dir = Path(self.tmpdir) / "prompts"
        self.prompts_dir.mkdir()
        self.schemas_dir = Path(self.tmpdir) / "schemas"
        self.schemas_dir.mkdir()

        # Write decision log
        (self.data_dir / "decision_log.csv").write_text(
            DECISION_HEADER + "\n" + DECISION_ROW + "\n"
        )

        # Write a sample prompt
        prompt_sub = self.prompts_dir / "test"
        prompt_sub.mkdir()
        (prompt_sub / "test_prompt.md").write_text("# Test Prompt\nDo things.\n")

        # Write policy files
        self.policy_dir = Path(self.tmpdir) / "governance"
        self.policy_dir.mkdir()
        self.policy_baseline = self.policy_dir / "POLICY_BASELINE.md"
        self.policy_baseline.write_text("# Test Policy\nRule 1.\n")
        self.policy_version = self.policy_dir / "POLICY_VERSION.txt"
        self.policy_version.write_text("GOV-TEST-1.0\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seal(self, decision_id: str = "DEC-TEST") -> Path:
        """Run seal_bundle and return path to sealed JSON."""
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", decision_id,
            "--user", "Tester",
            "--data-dir", str(self.data_dir),
            "--out-dir", str(self.out_dir),
            "--prompts-dir", str(self.prompts_dir),
            "--schemas-dir", str(self.schemas_dir),
            "--policy-baseline", str(self.policy_baseline),
            "--policy-version", str(self.policy_version),
            "--clock", FIXED_CLOCK,
            "--deterministic", "true",
        ]
        rc = seal_bundle.main()
        self.assertEqual(rc, 0, "seal_bundle should succeed")
        json_files = [
            f for f in self.out_dir.glob("RUN-*.json")
            if ".manifest." not in f.name
        ]
        self.assertEqual(len(json_files), 1, "Expected one sealed JSON")
        return json_files[0]


class TestSealAndReplay(ReconstructTestBase):
    """Test the full seal -> replay pipeline."""

    def test_seal_creates_valid_bundle(self) -> None:
        sealed_path = self._seal()

        # Sealed JSON should exist
        self.assertTrue(sealed_path.exists())

        # Manifest should exist
        manifest_files = list(self.out_dir.glob("*.manifest.json"))
        self.assertEqual(len(manifest_files), 1)

        # Load and check structure
        sealed = json.loads(sealed_path.read_text())
        self.assertEqual(sealed["schema_version"], "1.0")
        self.assertIn("authority_envelope", sealed)
        self.assertIn("decision_state", sealed)
        self.assertIn("inputs_snapshot", sealed)
        self.assertIn("hash_scope", sealed)
        self.assertIn("commit_hash", sealed)
        self.assertTrue(sealed["hash"].startswith("sha256:"))
        self.assertTrue(sealed["commit_hash"].startswith("sha256:"))

        # Check authority envelope
        env = sealed["authority_envelope"]
        self.assertEqual(env["envelope_version"], "1.0")
        self.assertEqual(env["actor"]["id"], "Tester")
        self.assertEqual(env["actor"]["role"], "Operator")
        self.assertEqual(env["policy_snapshot"]["policy_version"], "GOV-TEST-1.0")
        self.assertTrue(env["policy_snapshot"]["policy_hash"].startswith("sha256:"))
        self.assertTrue(env["refusal"]["refusal_available"])
        self.assertFalse(env["refusal"]["refusal_triggered"])
        self.assertTrue(env["enforcement"]["enforcement_emitted"])

        # Run ID should be deterministic (derived from hash)
        run_id = env["provenance"]["run_id"]
        self.assertTrue(run_id.startswith("RUN-"))
        commit_hash = sealed["commit_hash"]
        expected_prefix = "RUN-" + commit_hash.split(":")[1][:8]
        self.assertEqual(run_id, expected_prefix)

    def test_replay_passes_on_valid_bundle(self) -> None:
        sealed_path = self._seal()

        result = replay.replay(sealed_path)
        self.assertTrue(result.passed, f"Replay should pass. Failures: {result.failed_count}")
        self.assertEqual(result.exit_code, 0)

    def test_replay_fails_on_missing_authority(self) -> None:
        sealed_path = self._seal()

        # Corrupt: remove authority envelope
        sealed = json.loads(sealed_path.read_text())
        del sealed["authority_envelope"]
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed)

    def test_replay_fails_on_hash_tamper(self) -> None:
        sealed_path = self._seal()

        # Tamper: modify a field without recomputing hash
        sealed = json.loads(sealed_path.read_text())
        sealed["decision_state"]["title"] = "TAMPERED"
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed)

    def test_replay_detects_missing_scope(self) -> None:
        sealed_path = self._seal()

        # Corrupt: empty decisions scope
        sealed = json.loads(sealed_path.read_text())
        sealed["authority_envelope"]["scope_bound"]["decisions"] = []
        # Recompute hash so only scope check fails
        from canonical_json import sha256_text
        from canonical_json import canonical_dumps as cd
        sealed["hash"] = ""
        sealed["hash"] = sha256_text(cd(sealed))
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed)
        failed_names = [name for name, ok, _ in result.checks if not ok]
        self.assertIn("scope.decisions", failed_names)


    def test_schema_version_enforced(self) -> None:
        """Schema version must be '1.0' — replay rejects invalid versions."""
        sealed_path = self._seal()

        sealed = json.loads(sealed_path.read_text())
        self.assertEqual(sealed["schema_version"], "1.0")

        # Tamper: set invalid schema version
        sealed["schema_version"] = "0.0"
        # Recompute hash so only version check triggers
        from canonical_json import sha256_text
        from canonical_json import canonical_dumps as cd
        sealed["hash"] = ""
        sealed["hash"] = sha256_text(cd(sealed))
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed, "Replay should reject invalid schema_version")


class TestSealBundleErrors(ReconstructTestBase):
    """Test error handling in seal_bundle."""

    def test_missing_decision_id(self) -> None:
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-NONEXISTENT",
            "--data-dir", str(self.data_dir),
            "--out-dir", str(self.out_dir),
            "--prompts-dir", str(self.prompts_dir),
            "--schemas-dir", str(self.schemas_dir),
            "--policy-baseline", str(self.policy_baseline),
            "--policy-version", str(self.policy_version),
            "--clock", FIXED_CLOCK,
        ]
        rc = seal_bundle.main()
        self.assertEqual(rc, 1)

    def test_missing_data_dir(self) -> None:
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-TEST",
            "--data-dir", str(Path(self.tmpdir) / "nonexistent"),
            "--out-dir", str(self.out_dir),
            "--prompts-dir", str(self.prompts_dir),
            "--schemas-dir", str(self.schemas_dir),
            "--policy-baseline", str(self.policy_baseline),
            "--policy-version", str(self.policy_version),
            "--clock", FIXED_CLOCK,
        ]
        rc = seal_bundle.main()
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
