"""Tests for the transparency log: append, chaining, and verification."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from transparency_log_append import append_entry, verify_chain  # noqa: E402
from canonical_json import canonical_dumps, sha256_text  # noqa: E402
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


class TransparencyLogTestBase(unittest.TestCase):
    """Base class with a temp directory and log path."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.log_path = Path(self.tmpdir) / "transparency_log" / "log.ndjson"
        self.log_path.parent.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestTransparencyLogAppend(TransparencyLogTestBase):
    """Tests for append_entry chaining and structure."""

    def test_append_first_entry(self) -> None:
        """First entry has prev_entry_hash=None and entry_id starts with TLE-."""
        entry = append_entry(
            log_path=self.log_path,
            run_id="RUN-aaaa0001",
            commit_hash="sha256:aabbccdd",
            sealed_hash="sha256:11223344",
        )
        self.assertIsNone(entry["prev_entry_hash"])
        self.assertTrue(entry["entry_id"].startswith("TLE-"))
        self.assertTrue(entry["entry_hash"].startswith("sha256:"))
        self.assertEqual(entry["run_id"], "RUN-aaaa0001")
        self.assertEqual(entry["commit_hash"], "sha256:aabbccdd")

    def test_append_second_entry(self) -> None:
        """Second entry chains prev_entry_hash to first entry's hash."""
        first = append_entry(
            log_path=self.log_path,
            run_id="RUN-aaaa0001",
            commit_hash="sha256:aaaa",
            sealed_hash="sha256:bbbb",
        )
        second = append_entry(
            log_path=self.log_path,
            run_id="RUN-aaaa0002",
            commit_hash="sha256:cccc",
            sealed_hash="sha256:dddd",
        )

        self.assertEqual(second["prev_entry_hash"], first["entry_hash"])
        self.assertNotEqual(first["entry_hash"], second["entry_hash"])

    def test_entry_hash_integrity(self) -> None:
        """Re-hashing an entry with entry_hash='' matches the recorded entry_hash."""
        entry = append_entry(
            log_path=self.log_path,
            run_id="RUN-hash0001",
            commit_hash="sha256:1111",
            sealed_hash="sha256:2222",
        )

        # Recompute the hash the same way the module does
        copy = dict(entry)
        copy["entry_hash"] = ""
        computed = sha256_text(canonical_dumps(copy))

        self.assertEqual(computed, entry["entry_hash"],
                         "Recomputed entry hash should match recorded hash")


class TestTransparencyLogVerifyChain(TransparencyLogTestBase):
    """Tests for verify_chain integrity checks."""

    def test_verify_chain_valid(self) -> None:
        """A cleanly appended chain passes all verification checks."""
        for i in range(5):
            append_entry(
                log_path=self.log_path,
                run_id=f"RUN-chain{i:04d}",
                commit_hash=f"sha256:commit{i}",
                sealed_hash=f"sha256:sealed{i}",
            )

        results = verify_chain(self.log_path)
        all_passed = all(ok for _, ok, _ in results)
        self.assertTrue(all_passed,
                        f"All chain checks should pass. Failures: "
                        f"{[(ln, d) for ln, ok, d in results if not ok]}")

    def test_verify_chain_tampered(self) -> None:
        """Tampering with an entry causes verify_chain to catch the break."""
        for i in range(3):
            append_entry(
                log_path=self.log_path,
                run_id=f"RUN-tamper{i:04d}",
                commit_hash=f"sha256:commit{i}",
                sealed_hash=f"sha256:sealed{i}",
            )

        # Tamper the second entry's commit_hash
        lines = self.log_path.read_text().strip().split("\n")
        entry = json.loads(lines[1])
        entry["commit_hash"] = "sha256:TAMPERED"
        # Do NOT recompute entry_hash so the hash check fails
        lines[1] = json.dumps(entry, sort_keys=True)
        self.log_path.write_text("\n".join(lines) + "\n")

        results = verify_chain(self.log_path)
        failed = [(ln, detail) for ln, ok, detail in results if not ok]
        self.assertTrue(len(failed) > 0,
                        "Should detect at least one chain integrity failure")


class SealedWithTransparencyBase(unittest.TestCase):
    """Base class that seals a decision and creates a transparency log entry."""

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
        self.log_path = Path(self.tmpdir) / "transparency_log" / "log.ndjson"
        self.log_path.parent.mkdir(parents=True)

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


class TestReplayWithTransparency(SealedWithTransparencyBase):
    """Tests for replay with verify_transparency=True."""

    def test_replay_with_transparency(self) -> None:
        """Replay passes when transparency log contains the matching entry."""
        sealed_path = self._seal()
        sealed = json.loads(sealed_path.read_text())

        # Append the entry to the transparency log
        run_id = sealed["authority_envelope"]["provenance"]["run_id"]
        append_entry(
            log_path=self.log_path,
            run_id=run_id,
            commit_hash=sealed["commit_hash"],
            sealed_hash=sealed["hash"],
        )

        result = replay.replay(
            sealed_path,
            verify_transparency=True,
            transparency_log=self.log_path,
        )
        self.assertTrue(result.passed,
                        f"Replay+transparency should pass. Failures: "
                        f"{[n for n, ok, _ in result.checks if not ok]}")

        # Verify transparency-specific checks passed
        t_checks = [(n, ok) for n, ok, _ in result.checks if "transparency" in n]
        self.assertTrue(len(t_checks) > 0, "Should have transparency checks")
        for name, ok in t_checks:
            self.assertTrue(ok, f"Transparency check {name} should pass")


if __name__ == "__main__":
    unittest.main()
