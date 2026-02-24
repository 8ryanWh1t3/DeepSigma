"""Tests for multi-signature support: append, threshold, and tamper detection."""
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

import seal_bundle  # noqa: E402
import sign_artifact  # noqa: E402
import verify_multisig as vm  # noqa: E402
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


class MultisigTestBase(unittest.TestCase):
    """Base class that creates a sealed artifact for multisig testing."""

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
        (prompt_sub / "test_prompt.md").write_text("# Test Prompt\n")

        # Write policy files
        self.policy_dir = Path(self.tmpdir) / "governance"
        self.policy_dir.mkdir()
        self.policy_baseline = self.policy_dir / "POLICY_BASELINE.md"
        self.policy_baseline.write_text("# Test Policy\n")
        self.policy_version = self.policy_dir / "POLICY_VERSION.txt"
        self.policy_version.write_text("GOV-MULTISIG-1.0\n")

        # Generate two distinct HMAC keys
        self.key1 = base64.b64encode(secrets.token_bytes(32)).decode()
        self.key1_id = "ds-operator-2026-01"
        self.key2 = base64.b64encode(secrets.token_bytes(32)).decode()
        self.key2_id = "ds-witness-2026-01"

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
            if ".manifest." not in f.name and ".sig." not in f.name
        ]
        self.assertEqual(len(json_files), 1, "Expected one sealed JSON")
        return json_files[0]


class TestSingleSigAsMultisig(MultisigTestBase):
    """Tests for replay detecting a single signature via require_multisig."""

    def test_single_sig_as_multisig(self) -> None:
        """A single sig file is detected by replay with require_multisig=1."""
        sealed_path = self._seal()
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        result = replay.replay(
            sealed_path,
            verify_sig=True,
            key_b64=self.key1,
            require_multisig=1,
        )
        self.assertTrue(result.passed,
                        f"Replay with require_multisig=1 should pass on single sig. "
                        f"Failures: {[n for n, ok, _ in result.checks if not ok]}")


class TestAppendWitness(MultisigTestBase):
    """Tests for append_signature creating a multisig envelope."""

    def test_append_witness(self) -> None:
        """append_signature wraps an existing single sig into a multisig_version envelope."""
        sealed_path = self._seal()

        # Primary signature
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        # Append witness signature
        sig_path = sign_artifact.append_signature(
            sealed_path, "hmac", self.key2_id, self.key2,
            signer_id="witness-1", role="witness",
        )

        sig_data = json.loads(sig_path.read_text())
        self.assertIn("multisig_version", sig_data)
        self.assertEqual(sig_data["multisig_version"], "1.0")
        self.assertEqual(len(sig_data["signatures"]), 2)

        # Verify signer roles
        roles = {s["role"] for s in sig_data["signatures"]}
        self.assertIn("operator", roles)
        self.assertIn("witness", roles)


class TestMultisigThreshold(MultisigTestBase):
    """Tests for threshold enforcement in verify_multisig."""

    def test_threshold_not_met(self) -> None:
        """1 signature with require_multisig=2 fails quorum check."""
        sealed_path = self._seal()

        # Only primary signature
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        result = replay.replay(
            sealed_path,
            verify_sig=True,
            key_b64=self.key1,
            require_multisig=2,
        )
        self.assertFalse(result.passed,
                         "Should fail: 1 sig with threshold=2")
        failed_names = [n for n, ok, _ in result.checks if not ok]
        self.assertTrue(
            any("multisig" in n for n in failed_names),
            f"Should fail on multisig threshold check. Failures: {failed_names}",
        )

    def test_threshold_met(self) -> None:
        """2 signatures with require_multisig=2 passes quorum check."""
        sealed_path = self._seal()

        # Primary signature
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        # Append witness
        sign_artifact.append_signature(
            sealed_path, "hmac", self.key2_id, self.key2,
            signer_id="witness-1", role="witness",
        )

        result = replay.replay(
            sealed_path,
            require_multisig=2,
        )
        # Multisig threshold check should pass (count check, not crypto verify)
        ms_checks = [(n, ok) for n, ok, _ in result.checks if "multisig.threshold" in n]
        self.assertTrue(len(ms_checks) > 0, "Should have multisig.threshold check")
        for name, ok in ms_checks:
            self.assertTrue(ok, f"Multisig threshold check {name} should pass")


class TestMultisigTamperDetection(MultisigTestBase):
    """Tests for tamper detection via verify_multisig."""

    def test_tampered_fails(self) -> None:
        """Tampering sealed JSON after signing causes verify_multisig to fail."""
        sealed_path = self._seal()

        # Primary signature
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        # Append witness to create multisig envelope
        sig_path = sign_artifact.append_signature(
            sealed_path, "hmac", self.key2_id, self.key2,
            signer_id="witness-1", role="witness",
        )

        # Tamper the sealed artifact AFTER signing
        data = json.loads(sealed_path.read_text())
        data["decision_state"]["title"] = "TAMPERED"
        sealed_path.write_text(json.dumps(data))

        # verify_multisig should fail — canonical bytes changed
        vr = vm.verify_multisig(
            artifact_path=sealed_path,
            multisig_path=sig_path,
            threshold=2,
            key_b64=self.key1,
            keys={self.key2_id: self.key2},
        )
        self.assertFalse(vr.valid if hasattr(vr, 'valid') else vr.passed,
                         "Multisig verification should fail after tamper")


class TestReplayRequireMultisig(MultisigTestBase):
    """Full replay with require_multisig=2 after two signatures."""

    def test_replay_require_multisig(self) -> None:
        """Full replay with require_multisig=2 passes after operator + witness sign."""
        sealed_path = self._seal()

        # Primary signature
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key1_id, self.key1,
            signer_id="operator", role="operator",
        )

        # Append witness
        sign_artifact.append_signature(
            sealed_path, "hmac", self.key2_id, self.key2,
            signer_id="witness-1", role="witness",
        )

        result = replay.replay(
            sealed_path,
            require_multisig=2,
        )

        # Check the multisig threshold passed
        ms_checks = [(n, ok, d) for n, ok, d in result.checks if "multisig" in n]
        self.assertTrue(len(ms_checks) > 0, "Should have multisig checks")

        threshold_checks = [(n, ok) for n, ok, _ in ms_checks if "threshold" in n]
        for name, ok in threshold_checks:
            self.assertTrue(ok, f"Multisig threshold {name} should pass with 2 sigs")


if __name__ == "__main__":
    unittest.main()
