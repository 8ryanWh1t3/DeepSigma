"""Tests for the seal_and_prove orchestration pipeline."""
from __future__ import annotations

import base64
import json
import secrets
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from seal_and_prove import seal_and_prove  # noqa: E402

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


class SealAndProveTestBase(unittest.TestCase):
    """Base class that sets up an isolated workspace for seal_and_prove."""

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

        # Generate fresh HMAC key
        self.sign_key = base64.b64encode(secrets.token_bytes(32)).decode()
        self.sign_key_id = "ds-test-2026-01"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_pipeline(self, **kwargs) -> dict:
        """Run seal_and_prove with test defaults, accepting overrides."""
        defaults = dict(
            decision_id="DEC-TEST",
            clock=FIXED_CLOCK,
            sign_algo="hmac",
            sign_key_id=self.sign_key_id,
            sign_key=self.sign_key,
            user="Tester",
            data_dir=self.data_dir,
            out_dir=self.out_dir,
            prompts_dir=self.prompts_dir,
            schemas_dir=self.schemas_dir,
            policy_baseline=self.policy_baseline,
            policy_version_file=self.policy_version,
            transparency_log=self.log_path,
        )
        defaults.update(kwargs)
        return seal_and_prove(**defaults)


class TestBasicSealAndProve(SealAndProveTestBase):
    """Tests for the core pipeline output."""

    def test_basic_seal_and_prove(self) -> None:
        """Returns dict with expected keys and no errors."""
        summary = self._run_pipeline()

        self.assertIn("decision_id", summary)
        self.assertEqual(summary["decision_id"], "DEC-TEST")
        self.assertIn("run_id", summary)
        self.assertTrue(summary["run_id"].startswith("RUN-"))
        self.assertIn("commit_hash", summary)
        self.assertTrue(summary["commit_hash"].startswith("sha256:"))
        self.assertIn("content_hash", summary)
        self.assertTrue(summary["content_hash"].startswith("sha256:"))
        self.assertIn("sealed_path", summary)
        self.assertIn("manifest_path", summary)
        self.assertIn("sig_paths", summary)
        self.assertIn("errors", summary)
        self.assertEqual(len(summary["errors"]), 0,
                         f"Pipeline should have no errors: {summary['errors']}")


class TestProducesPack(SealAndProveTestBase):
    """Tests for the admissibility pack directory."""

    def test_produces_pack(self) -> None:
        """pack_dir contains expected files after a full run."""
        pack_dir = Path(self.tmpdir) / "pack"
        self._run_pipeline(pack_dir=pack_dir)

        self.assertTrue(pack_dir.exists(), "Pack dir should be created")

        # Should contain at least: sealed JSON, manifest, sig files, transparency log
        pack_files = list(pack_dir.iterdir())
        pack_names = [f.name for f in pack_files]

        # Check sealed run JSON
        sealed_json = [f for f in pack_names if f.startswith("RUN-") and f.endswith(".json") and ".manifest." not in f and ".sig." not in f]
        self.assertTrue(len(sealed_json) >= 1, f"Pack should contain sealed JSON. Files: {pack_names}")

        # Check manifest
        manifests = [f for f in pack_names if ".manifest.json" in f]
        self.assertTrue(len(manifests) >= 1, f"Pack should contain manifest. Files: {pack_names}")

        # Check sig files
        sig_files = [f for f in pack_names if ".sig.json" in f]
        self.assertTrue(len(sig_files) >= 1, f"Pack should contain sig files. Files: {pack_names}")

        # Check transparency log
        self.assertIn("transparency_log.ndjson", pack_names,
                       f"Pack should contain transparency log. Files: {pack_names}")


class TestTransparencyLogAppended(SealAndProveTestBase):
    """Tests for transparency log integration."""

    def test_transparency_log_appended(self) -> None:
        """log.ndjson has an entry after the pipeline runs."""
        summary = self._run_pipeline()

        self.assertTrue(self.log_path.exists(), "Transparency log should exist")
        text = self.log_path.read_text().strip()
        self.assertTrue(len(text) > 0, "Transparency log should not be empty")

        lines = text.split("\n")
        self.assertEqual(len(lines), 1, "Should have exactly one entry")

        entry = json.loads(lines[0])
        self.assertEqual(entry["commit_hash"], summary["commit_hash"])
        self.assertTrue(entry["entry_id"].startswith("TLE-"))
        self.assertIsNotNone(summary["transparency_entry"])


class TestSelfReplayPasses(SealAndProveTestBase):
    """Tests for the built-in replay self-check."""

    def test_self_replay_passes(self) -> None:
        """replay_passed is True in the summary."""
        summary = self._run_pipeline()
        self.assertTrue(summary["replay_passed"],
                        f"Self-replay should pass. Errors: {summary['errors']}")


class TestAuditPasses(SealAndProveTestBase):
    """Tests for the built-in determinism audit self-check."""

    def test_audit_passes(self) -> None:
        """audit_clean is True in the summary."""
        summary = self._run_pipeline()
        self.assertTrue(summary["audit_clean"],
                        f"Determinism audit should be clean. Errors: {summary['errors']}")


class TestWithWitness(SealAndProveTestBase):
    """Tests for witness key support."""

    def test_with_witness(self) -> None:
        """witness_keys adds additional signatures to the sealed artifact."""
        witness_key = base64.b64encode(secrets.token_bytes(32)).decode()
        witness_keys = [
            {
                "key_b64": witness_key,
                "key_id": "ds-witness-2026-01",
                "signer_id": "reviewer-1",
                "role": "reviewer",
                "algo": "hmac",
            },
        ]

        # Skip the built-in replay self-check: seal_and_prove runs replay
        # with verify_sig=True, which does single-sig verification on the
        # now-multisig envelope. Instead, verify artifacts directly.
        summary = self._run_pipeline(
            witness_keys=witness_keys,
            no_replay_check=True,
        )

        # Should have at least 3 sig paths:
        # sealed sig, manifest sig, + witness appended to sealed sig
        self.assertGreaterEqual(len(summary["sig_paths"]), 3,
                                f"Should have 3+ sig paths with witness. Got: {summary['sig_paths']}")

        # The sealed run's sig file should now be a multisig envelope
        sealed_path = Path(summary["sealed_path"])
        sig_path = Path(str(sealed_path) + ".sig.json")
        self.assertTrue(sig_path.exists(), "Sig file should exist")

        sig_data = json.loads(sig_path.read_text())
        self.assertIn("multisig_version", sig_data,
                       "Witness should produce multisig envelope")
        self.assertEqual(len(sig_data["signatures"]), 2,
                         "Should have 2 signatures (operator + witness)")

        # Verify the multisig envelope passes threshold verification directly
        from verify_multisig import verify_multisig
        vr = verify_multisig(
            artifact_path=sealed_path,
            multisig_path=sig_path,
            threshold=2,
            keys={
                self.sign_key_id: self.sign_key,
                "ds-witness-2026-01": witness_key,
            },
        )
        self.assertTrue(vr.passed,
                        f"Multisig verification should pass. "
                        f"Checks: {[(n, ok, d) for n, ok, d in vr.checks if not ok]}")

        # Verify replay passes with require_multisig (count check, no sig verify)
        from replay_sealed_run import replay
        result = replay(
            sealed_path,
            require_multisig=2,
        )
        ms_threshold = [(n, ok) for n, ok, _ in result.checks if "multisig.threshold" in n]
        self.assertTrue(len(ms_threshold) > 0, "Should have multisig.threshold check")
        for name, ok in ms_threshold:
            self.assertTrue(ok, f"Multisig threshold {name} should pass")


if __name__ == "__main__":
    unittest.main()
