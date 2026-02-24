"""Tests for Merkle tree primitives and commitment roots."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from merkle import merkle_root, verify_merkle_root, EMPTY_ROOT  # noqa: E402
from canonical_json import sha256_text  # noqa: E402
import build_commitments  # noqa: E402
import seal_bundle  # noqa: E402
import replay_sealed_run as replay  # noqa: E402

FIXED_CLOCK = "2026-02-21T00:00:00Z"

DECISION_HEADER = (
    "DecisionID,Title,Category,Owner,Status,Confidence_pct,"
    "BlastRadius_1to5,Reversibility_1to5,CostOfDelay,CompressionRisk,"
    "Evidence,CounterEvidence,Assumptions,DateLogged,ReviewDate,PriorityScore,Notes"
)
DECISION_ROW = (
    "DEC-TEST,Test decision,Tech,Tester,Active,80,"
    "2,3,Low,Low,Evidence,None,Stable,2026-01-01,2026-04-01,5.0,test"
)


class TestMerkleTreePrimitives(unittest.TestCase):
    """Unit tests for the merkle_root function."""

    def test_empty_tree(self) -> None:
        """Empty leaf list returns the canonical EMPTY_ROOT sentinel."""
        result = merkle_root([])
        self.assertEqual(result, EMPTY_ROOT)

    def test_single_leaf(self) -> None:
        """Single leaf produces a sha256-prefixed root string."""
        leaf = sha256_text("abc")
        result = merkle_root([leaf])
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("sha256:"),
                        f"Expected sha256: prefix, got {result[:20]}")

    def test_two_leaves(self) -> None:
        """Two leaves produce a deterministic root that verify_merkle_root accepts."""
        leaves = [sha256_text("a"), sha256_text("b")]
        root = merkle_root(leaves)
        self.assertTrue(root.startswith("sha256:"))
        self.assertTrue(verify_merkle_root(leaves, root))

    def test_three_leaves_odd(self) -> None:
        """Odd leaf count pads the last leaf (three leaves still works)."""
        leaves = [sha256_text("x"), sha256_text("y"), sha256_text("z")]
        root = merkle_root(leaves)
        self.assertTrue(root.startswith("sha256:"))
        self.assertTrue(verify_merkle_root(leaves, root))

    def test_deterministic(self) -> None:
        """Same input leaves produce the same root every time."""
        leaves = [sha256_text("foo"), sha256_text("bar"), sha256_text("baz")]
        root1 = merkle_root(leaves)
        root2 = merkle_root(leaves)
        self.assertEqual(root1, root2)

    def test_order_matters(self) -> None:
        """Different leaf order produces a different root."""
        a, b = sha256_text("alpha"), sha256_text("beta")
        root_ab = merkle_root([a, b])
        root_ba = merkle_root([b, a])
        self.assertNotEqual(root_ab, root_ba)


class CommitmentTestBase(unittest.TestCase):
    """Base class that sets up a temp workspace for commitment / sealed tests."""

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

        # Write a sample schema
        (self.schemas_dir / "test_schema.json").write_text(
            json.dumps({"type": "object", "properties": {}})
        )

        # Write policy files
        self.policy_dir = Path(self.tmpdir) / "governance"
        self.policy_dir.mkdir()
        self.policy_baseline = self.policy_dir / "POLICY_BASELINE.md"
        self.policy_baseline.write_text("# Test Policy\nRule 1.\n")
        self.policy_version = self.policy_dir / "POLICY_VERSION.txt"
        self.policy_version.write_text("GOV-TEST-1.0\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seal(self) -> Path:
        """Seal a decision and return the sealed JSON path."""
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-TEST",
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


class TestBuildCommitment(CommitmentTestBase):
    """Tests for build_commitment producing four Merkle roots."""

    def test_build_commitment_four_roots(self) -> None:
        """build_commitment returns dict with all four roots, leaf_count, and algorithm."""
        commitment = build_commitments.build_commitment(
            data_dir=self.data_dir,
            prompts_dir=self.prompts_dir,
            schemas_dir=self.schemas_dir,
            policy_baseline=self.policy_baseline,
        )
        self.assertIn("inputs_root", commitment)
        self.assertIn("prompts_root", commitment)
        self.assertIn("schemas_root", commitment)
        self.assertIn("policies_root", commitment)
        self.assertIn("leaf_count", commitment)
        self.assertIn("algorithm", commitment)

        self.assertTrue(commitment["inputs_root"].startswith("sha256:"))
        self.assertTrue(commitment["prompts_root"].startswith("sha256:"))
        self.assertTrue(commitment["schemas_root"].startswith("sha256:"))
        self.assertTrue(commitment["policies_root"].startswith("sha256:"))
        self.assertEqual(commitment["algorithm"], "sha256-merkle")
        self.assertGreater(commitment["leaf_count"], 0)


class TestSealedRunCommitments(CommitmentTestBase):
    """Tests for commitments embedded in sealed runs."""

    def test_sealed_run_contains_commitments(self) -> None:
        """Sealed run includes inputs_commitments key with four roots."""
        sealed_path = self._seal()
        sealed = json.loads(sealed_path.read_text())

        self.assertIn("inputs_commitments", sealed)
        commitments = sealed["inputs_commitments"]
        self.assertIn("inputs_root", commitments)
        self.assertIn("prompts_root", commitments)
        self.assertIn("schemas_root", commitments)
        self.assertIn("policies_root", commitments)
        self.assertTrue(commitments["inputs_root"].startswith("sha256:"))

    def test_replay_verifies_commitments(self) -> None:
        """Replay passes on a sealed run with valid commitments."""
        sealed_path = self._seal()
        result = replay.replay(sealed_path)
        self.assertTrue(result.passed,
                        f"Replay should pass. Failures: "
                        f"{[n for n, ok, _ in result.checks if not ok]}")

        # Specifically check commitment checks passed
        commitment_checks = [
            (n, ok) for n, ok, _ in result.checks if "commitments." in n
        ]
        self.assertTrue(len(commitment_checks) > 0,
                        "Should have at least one commitment check")
        for name, ok in commitment_checks:
            self.assertTrue(ok, f"Commitment check {name} should pass")

    def test_replay_detects_tampered_root(self) -> None:
        """Tampering inputs_commitments.inputs_root causes replay to fail."""
        sealed_path = self._seal()
        sealed = json.loads(sealed_path.read_text())

        # Tamper the inputs_root
        sealed["inputs_commitments"]["inputs_root"] = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        # Recompute content hash so the content hash check itself still passes,
        # isolating the commitment check failure
        sealed["hash"] = ""
        sealed["hash"] = sha256_text(json.dumps(
            sealed, sort_keys=True, separators=(",", ":"),
        ))
        sealed_path.write_text(json.dumps(sealed))

        result = replay.replay(sealed_path)
        self.assertFalse(result.passed,
                         "Replay should fail after tampering inputs_root")
        failed_names = [n for n, ok, _ in result.checks if not ok]
        self.assertTrue(
            any("commitments.inputs_root" in n for n in failed_names),
            f"Should detect inputs_root tamper. Failures: {failed_names}",
        )


if __name__ == "__main__":
    unittest.main()
