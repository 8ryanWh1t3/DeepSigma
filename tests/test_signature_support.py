"""Tests for cryptographic signature support (HMAC mode for CI)."""
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
import replay_sealed_run as replay  # noqa: E402
import sign_artifact  # noqa: E402
import verify_signature  # noqa: E402

FIXED_CLOCK = "2026-02-21T00:00:00Z"

# ── Sample data ──────────────────────────────────────────────────
DECISION_HEADER = (
    "DecisionID,Title,Category,Owner,Status,Confidence_pct,"
    "BlastRadius_1to5,Reversibility_1to5,CostOfDelay,CompressionRisk,"
    "Evidence,CounterEvidence,Assumptions,DateLogged,ReviewDate,PriorityScore,Notes"
)
DECISION_ROW = (
    "DEC-SIG,Signature test decision,Tech,Tester,Active,80,"
    "2,3,Low,Low,Evidence,None,Stable,2026-01-01,2026-04-01,5.0,sig test"
)


class SignatureTestBase(unittest.TestCase):
    """Base class that creates a sealed artifact for signature testing."""

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

        prompt_sub = self.prompts_dir / "test"
        prompt_sub.mkdir()
        (prompt_sub / "test_prompt.md").write_text("# Test Prompt\n")

        self.policy_dir = Path(self.tmpdir) / "governance"
        self.policy_dir.mkdir()
        self.policy_baseline = self.policy_dir / "POLICY_BASELINE.md"
        self.policy_baseline.write_text("# Test Policy\n")
        self.policy_version = self.policy_dir / "POLICY_VERSION.txt"
        self.policy_version.write_text("GOV-SIG-1.0\n")

        # Generate a test HMAC key
        self.test_key = base64.b64encode(secrets.token_bytes(32)).decode()
        self.key_id = "ds-test-2026-01"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seal(self) -> Path:
        """Seal a decision and return the sealed JSON path."""
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-SIG",
            "--user", "SigTester",
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
        self.assertEqual(rc, 0)
        json_files = [
            f for f in self.out_dir.glob("RUN-*.json")
            if ".manifest." not in f.name and ".sig." not in f.name
        ]
        self.assertEqual(len(json_files), 1)
        return json_files[0]


class TestHmacSignAndVerify(SignatureTestBase):
    """Sign with HMAC and verify."""

    def test_sign_creates_sig_file(self) -> None:
        sealed_path = self._seal()
        sig_path = sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key_id, self.test_key,
        )
        self.assertTrue(sig_path.exists())
        sig = json.loads(sig_path.read_text())
        self.assertEqual(sig["sig_version"], "1.0")
        self.assertEqual(sig["algorithm"], "hmac-sha256")
        self.assertEqual(sig["signing_key_id"], self.key_id)
        self.assertEqual(sig["payload_type"], "sealed_run")
        self.assertTrue(sig["payload_commit_hash"].startswith("sha256:"))
        self.assertTrue(sig["payload_bytes_sha256"].startswith("sha256:"))
        self.assertIsNotNone(sig["signature"])
        self.assertIsNone(sig["public_key"])

    def test_verify_passes_on_valid_signature(self) -> None:
        sealed_path = self._seal()
        sig_path = sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key_id, self.test_key,
        )

        result = verify_signature.verify(sealed_path, sig_path, key_b64=self.test_key)
        self.assertTrue(result.passed, f"Verify should pass. Checks: {result.checks}")

    def test_verify_fails_on_wrong_key(self) -> None:
        sealed_path = self._seal()
        sig_path = sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key_id, self.test_key,
        )

        wrong_key = base64.b64encode(secrets.token_bytes(32)).decode()
        result = verify_signature.verify(sealed_path, sig_path, key_b64=wrong_key)
        self.assertFalse(result.passed)

    def test_verify_fails_on_tampered_artifact(self) -> None:
        sealed_path = self._seal()
        sig_path = sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key_id, self.test_key,
        )

        # Tamper with artifact
        data = json.loads(sealed_path.read_text())
        data["decision_state"]["title"] = "TAMPERED"
        sealed_path.write_text(json.dumps(data))

        result = verify_signature.verify(sealed_path, sig_path, key_b64=self.test_key)
        self.assertFalse(result.passed)


class TestSealBundleWithSigning(SignatureTestBase):
    """Test integrated signing via seal_bundle --sign."""

    def test_seal_with_sign_produces_sig_files(self) -> None:
        sys.argv = [
            "seal_bundle.py",
            "--decision-id", "DEC-SIG",
            "--user", "SigTester",
            "--data-dir", str(self.data_dir),
            "--out-dir", str(self.out_dir),
            "--prompts-dir", str(self.prompts_dir),
            "--schemas-dir", str(self.schemas_dir),
            "--policy-baseline", str(self.policy_baseline),
            "--policy-version", str(self.policy_version),
            "--clock", FIXED_CLOCK,
            "--sign", "true",
            "--sign-algo", "hmac",
            "--sign-key-id", self.key_id,
            "--sign-key", self.test_key,
        ]
        rc = seal_bundle.main()
        self.assertEqual(rc, 0)

        sig_files = list(self.out_dir.glob("*.sig.json"))
        self.assertEqual(len(sig_files), 2, "Should produce 2 sig files (sealed + manifest)")


class TestReplayWithSignatureVerification(SignatureTestBase):
    """Test replay with --verify-signature."""

    def test_replay_with_valid_signature(self) -> None:
        sealed_path = self._seal()
        sign_artifact.sign_artifact(
            sealed_path, "hmac", self.key_id, self.test_key,
        )

        result = replay.replay(
            sealed_path,
            verify_sig=True,
            key_b64=self.test_key,
        )
        self.assertTrue(result.passed,
                        f"Replay+sig should pass. Failed: {[n for n, ok, _ in result.checks if not ok]}")

    def test_replay_fails_with_missing_signature(self) -> None:
        sealed_path = self._seal()
        # Don't create a sig file

        result = replay.replay(
            sealed_path,
            verify_sig=True,
            key_b64=self.test_key,
        )
        self.assertFalse(result.passed)
        failed = [n for n, ok, _ in result.checks if not ok]
        self.assertTrue(any("signature" in n for n in failed))


class TestManifestSigning(SignatureTestBase):
    """Test signing manifests."""

    def test_sign_manifest(self) -> None:
        self._seal()
        manifest_files = list(self.out_dir.glob("*.manifest.json"))
        self.assertEqual(len(manifest_files), 1)

        sig_path = sign_artifact.sign_artifact(
            manifest_files[0], "hmac", self.key_id, self.test_key,
        )
        sig = json.loads(sig_path.read_text())
        self.assertEqual(sig["payload_type"], "manifest")

        result = verify_signature.verify(manifest_files[0], sig_path, key_b64=self.test_key)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
