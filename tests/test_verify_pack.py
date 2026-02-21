"""Tests for verify_pack one-command verifier."""
from __future__ import annotations

import base64
import json
import secrets
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from seal_and_prove import seal_and_prove  # noqa: E402
from verify_pack import verify_pack  # noqa: E402

FIXED_CLOCK = "2026-02-21T00:00:00Z"

# Test data paths
DATA_DIR = REPO_ROOT / "artifacts" / "sample_data" / "prompt_os_v2"
PROMPTS_DIR = REPO_ROOT / "prompts"
SCHEMAS_DIR = REPO_ROOT / "schemas"
POLICY_BASELINE = REPO_ROOT / "docs" / "governance" / "POLICY_BASELINE.md"
POLICY_VERSION = REPO_ROOT / "docs" / "governance" / "POLICY_VERSION.txt"


class VerifyPackTestBase(unittest.TestCase):
    """Base class that generates a valid pack in tmpdir."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.sign_key = base64.b64encode(secrets.token_bytes(32)).decode()
        self.sign_key_id = "ds-test-2026-01"
        self.pack_dir = Path(self.tmpdir) / "pack"
        self.sealed_dir = Path(self.tmpdir) / "sealed"
        self.log_path = Path(self.tmpdir) / "log.ndjson"
        self.ledger_path = Path(self.tmpdir) / "ledger.ndjson"

        # Generate a complete pack
        self.summary = seal_and_prove(
            decision_id="DEC-001",
            clock=FIXED_CLOCK,
            sign_algo="hmac",
            sign_key_id=self.sign_key_id,
            sign_key=self.sign_key,
            user="TestOperator",
            data_dir=DATA_DIR,
            out_dir=self.sealed_dir,
            prompts_dir=PROMPTS_DIR,
            schemas_dir=SCHEMAS_DIR,
            policy_baseline=POLICY_BASELINE,
            policy_version_file=POLICY_VERSION,
            transparency_log=self.log_path,
            pack_dir=self.pack_dir,
            auto_authority=True,
            authority_ledger=self.ledger_path,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestVerifyValidPack(VerifyPackTestBase):
    def test_all_checks_pass(self) -> None:
        result = verify_pack(self.pack_dir, key_b64=self.sign_key)
        self.assertTrue(result.passed, f"Failed checks: {[(n, d) for _, checks in result.sections for n, ok, d in checks if not ok]}")
        self.assertGreater(result.total_checks, 0)


class TestVerifyTamperedSealed(VerifyPackTestBase):
    def test_tampered_sealed_fails(self) -> None:
        # Find sealed run in pack
        sealed_files = [f for f in self.pack_dir.glob("*.json")
                        if not f.name.endswith(".sig.json")
                        and not f.name.endswith(".manifest.json")
                        and f.name not in ("transparency_log.ndjson", "authority_ledger.ndjson")]
        self.assertTrue(len(sealed_files) > 0)

        sealed = sealed_files[0]
        data = json.loads(sealed.read_text())
        data["decision_state"]["title"] = "TAMPERED"
        sealed.write_text(json.dumps(data, indent=2, sort_keys=True))

        result = verify_pack(self.pack_dir, key_b64=self.sign_key)
        self.assertFalse(result.passed)


class TestVerifyTamperedSignature(VerifyPackTestBase):
    def test_tampered_sig_fails(self) -> None:
        sig_files = list(self.pack_dir.glob("*.sig.json"))
        self.assertTrue(len(sig_files) > 0)

        sig = sig_files[0]
        data = json.loads(sig.read_text())
        data["signature"] = "AAAA" + data.get("signature", "")[4:]
        sig.write_text(json.dumps(data, indent=2, sort_keys=True))

        result = verify_pack(self.pack_dir, key_b64=self.sign_key)
        self.assertFalse(result.passed)


class TestVerifyMissingAuthority(VerifyPackTestBase):
    def test_missing_authority_ledger(self) -> None:
        # Remove authority ledger
        ledger = self.pack_dir / "authority_ledger.ndjson"
        if ledger.exists():
            ledger.unlink()

        # Should still work (authority is optional if not present)
        result = verify_pack(self.pack_dir, key_b64=self.sign_key)
        # The sealed run still has authority_ledger_ref but ledger is gone
        # replay won't verify authority since has_ledger is False
        # This should pass since we don't verify authority without the file
        self.assertTrue(result.passed)


class TestVerifyExpiredAuthority(VerifyPackTestBase):
    def test_expired_authority_detected(self) -> None:
        # Modify authority ledger to set expires_at in the past
        ledger = self.pack_dir / "authority_ledger.ndjson"
        if not ledger.exists():
            return

        lines = ledger.read_text().strip().split("\n")
        new_lines = []
        for line in lines:
            entry = json.loads(line)
            if entry.get("grant_type") != "revocation":
                entry["expires_at"] = "2026-02-20T00:00:00Z"  # Before FIXED_CLOCK
            new_lines.append(json.dumps(entry, sort_keys=True))
        ledger.write_text("\n".join(new_lines) + "\n")

        result = verify_pack(self.pack_dir, key_b64=self.sign_key)
        # Should fail because authority expired before commit time
        self.assertFalse(result.passed)


class TestVerifyPackNoKey(VerifyPackTestBase):
    def test_no_key_skips_sig(self) -> None:
        result = verify_pack(self.pack_dir)
        # Should still pass structural checks (no sig verification without key)
        # Authority ledger entry_hash will mismatch if we didn't tamper
        # Actually verify_pack without key just skips sig check
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
