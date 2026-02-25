"""Tests for ABP v1 — Authority Boundary Primitive."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from build_abp import (  # noqa: E402
    build_abp,
    compose_abps,
    verify_abp_hash,
    verify_abp_id,
    write_abp,
)
from verify_abp import verify_abp, VerifyAbpResult  # noqa: E402

FIXED_CLOCK = "2026-02-24T00:00:00Z"
SCHEMA_PATH = REPO_ROOT / "schemas" / "reconstruct" / "abp_v1.json"

DEMO_SCOPE = {
    "contract_id": "CTR-TEST-001",
    "program": "TESTPROG",
    "modules": ["hiring", "compliance"],
}

DEMO_AUTH_REF = {
    "authority_entry_id": "AUTH-aabbccdd",
    "authority_entry_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000001",
    "authority_ledger_path": "ledger.ndjson",
}


def _build_test_ledger(tmpdir: str, entry_id: str = "AUTH-aabbccdd",
                       revoked: bool = False) -> Path:
    """Create a minimal test ledger for authority ref verification."""
    from canonical_json import canonical_dumps, sha256_text

    entry = {
        "entry_version": "1.0",
        "entry_id": entry_id,
        "authority_id": "AUTO-TEST",
        "actor_id": "tester",
        "actor_role": "Operator",
        "grant_type": "direct",
        "scope_bound": {"decisions": ["DEC-TEST"], "claims": [], "patches": [], "prompts": [], "datasets": []},
        "policy_version": "GOV-1.0",
        "policy_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "effective_at": "2026-01-01T00:00:00Z",
        "expires_at": None,
        "revoked_at": "2026-03-01T00:00:00Z" if revoked else None,
        "revocation_reason": "test revocation" if revoked else None,
        "witness_required": False,
        "witness_role": None,
        "signing_key_id": None,
        "signature_ref": None,
        "commit_hash_refs": [],
        "notes": "",
        "prev_entry_hash": None,
        "entry_hash": "",
        "observed_at": "2026-01-01T00:00:00Z",
    }
    copy = dict(entry)
    copy["entry_hash"] = ""
    entry["entry_hash"] = sha256_text(canonical_dumps(copy))

    ledger_path = Path(tmpdir) / "ledger.ndjson"
    ledger_path.write_text(json.dumps(entry, sort_keys=True) + "\n")
    return ledger_path, entry["entry_hash"]


class TestBuildAbpBasic(unittest.TestCase):
    """Test basic ABP construction."""

    def test_build_abp_basic(self):
        abp = build_abp(
            scope=DEMO_SCOPE,
            authority_ref=DEMO_AUTH_REF,
            clock=FIXED_CLOCK,
        )
        required_keys = [
            "abp_version", "abp_id", "scope", "authority_ref", "objectives",
            "tools", "data", "approvals", "escalation", "runtime", "proof",
            "composition", "effective_at", "expires_at", "created_at", "hash",
        ]
        for key in required_keys:
            self.assertIn(key, abp, f"Missing required key: {key}")
        self.assertEqual(abp["abp_version"], "1.0")
        self.assertTrue(abp["abp_id"].startswith("ABP-"))
        self.assertEqual(len(abp["abp_id"]), 12)  # ABP- + 8 hex
        self.assertTrue(abp["hash"].startswith("sha256:"))

    def test_abp_defaults_empty_sections(self):
        abp = build_abp(
            scope=DEMO_SCOPE,
            authority_ref=DEMO_AUTH_REF,
            clock=FIXED_CLOCK,
        )
        self.assertEqual(abp["objectives"], {"allowed": [], "denied": []})
        self.assertEqual(abp["tools"], {"allow": [], "deny": []})
        self.assertEqual(abp["data"], {"permissions": []})
        self.assertEqual(abp["approvals"], {"required": []})
        self.assertEqual(abp["escalation"], {"paths": []})
        self.assertEqual(abp["runtime"], {"validators": []})

    def test_abp_with_all_sections(self):
        abp = build_abp(
            scope=DEMO_SCOPE,
            authority_ref=DEMO_AUTH_REF,
            objectives={"allowed": [{"id": "O1", "description": "test"}], "denied": []},
            tools={"allow": [{"name": "seal", "scope": None}], "deny": []},
            data={"permissions": [{"resource": "x", "operations": ["read"], "roles": ["Op"], "sensitivity": "internal"}]},
            approvals={"required": [{"action": "seal", "approver_role": "Rev", "threshold": 1, "timeout_ms": None}]},
            escalation={"paths": [{"trigger": "fail", "destination": "Rev", "severity": "warn", "auto": True}]},
            runtime={"validators": [{"name": "v1", "when": "pre_action", "fail_action": "block", "config": {}}]},
            proof={"required": ["seal", "manifest"]},
            clock=FIXED_CLOCK,
        )
        self.assertEqual(len(abp["objectives"]["allowed"]), 1)
        self.assertEqual(len(abp["tools"]["allow"]), 1)
        self.assertEqual(len(abp["data"]["permissions"]), 1)


class TestAbpDeterminism(unittest.TestCase):
    """Test deterministic ID and hash generation."""

    def test_hash_deterministic(self):
        abp1 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp2 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        self.assertEqual(abp1["hash"], abp2["hash"])

    def test_id_deterministic(self):
        abp1 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp2 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        self.assertEqual(abp1["abp_id"], abp2["abp_id"])

    def test_different_scope_different_id(self):
        abp1 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        scope2 = dict(DEMO_SCOPE, contract_id="CTR-OTHER")
        abp2 = build_abp(scope=scope2, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        self.assertNotEqual(abp1["abp_id"], abp2["abp_id"])

    def test_different_clock_different_id(self):
        abp1 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp2 = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock="2026-03-01T00:00:00Z")
        self.assertNotEqual(abp1["abp_id"], abp2["abp_id"])


class TestAbpHashVerify(unittest.TestCase):
    """Test hash integrity verification."""

    def test_hash_verify_passes(self):
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        self.assertTrue(verify_abp_hash(abp))

    def test_tamper_detected(self):
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp["scope"]["program"] = "TAMPERED"
        self.assertFalse(verify_abp_hash(abp))

    def test_id_verify_passes(self):
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        self.assertTrue(verify_abp_id(abp))

    def test_id_tamper_detected(self):
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp["abp_id"] = "ABP-00000000"
        self.assertFalse(verify_abp_id(abp))


class TestAbpComposition(unittest.TestCase):
    """Test ABP composition (parent from children)."""

    def test_compose_basic(self):
        child1 = build_abp(
            scope={"contract_id": "CTR-C1", "program": "P", "modules": ["hiring"]},
            authority_ref=DEMO_AUTH_REF,
            objectives={"allowed": [{"id": "O1", "description": "Hire"}], "denied": []},
            tools={"allow": [{"name": "t1", "scope": None}], "deny": []},
            clock=FIXED_CLOCK,
        )
        child2 = build_abp(
            scope={"contract_id": "CTR-C2", "program": "P", "modules": ["compliance"]},
            authority_ref=DEMO_AUTH_REF,
            objectives={"allowed": [{"id": "O2", "description": "Comply"}], "denied": []},
            tools={"allow": [{"name": "t2", "scope": None}], "deny": []},
            clock=FIXED_CLOCK,
        )
        parent = compose_abps(
            parent_scope={"contract_id": "CTR-PARENT", "program": "P", "modules": ["hiring", "compliance"]},
            parent_authority_ref=DEMO_AUTH_REF,
            children=[child1, child2],
            clock=FIXED_CLOCK,
        )
        self.assertEqual(len(parent["composition"]["children"]), 2)
        self.assertEqual(parent["composition"]["children"][0]["abp_id"], child1["abp_id"])
        self.assertEqual(parent["composition"]["children"][1]["abp_id"], child2["abp_id"])
        self.assertEqual(len(parent["objectives"]["allowed"]), 2)
        self.assertEqual(len(parent["tools"]["allow"]), 2)
        self.assertTrue(verify_abp_hash(parent))


class TestAbpContradictions(unittest.TestCase):
    """Test contradiction detection."""

    def test_tool_contradiction_raises(self):
        with self.assertRaises(ValueError) as ctx:
            build_abp(
                scope=DEMO_SCOPE,
                authority_ref=DEMO_AUTH_REF,
                tools={
                    "allow": [{"name": "seal_bundle", "scope": None}],
                    "deny": [{"name": "seal_bundle", "reason": "nope"}],
                },
                clock=FIXED_CLOCK,
            )
        self.assertIn("seal_bundle", str(ctx.exception))

    def test_objective_contradiction_raises(self):
        with self.assertRaises(ValueError) as ctx:
            build_abp(
                scope=DEMO_SCOPE,
                authority_ref=DEMO_AUTH_REF,
                objectives={
                    "allowed": [{"id": "OBJ-1", "description": "do it"}],
                    "denied": [{"id": "OBJ-1", "description": "dont", "reason": "no"}],
                },
                clock=FIXED_CLOCK,
            )
        self.assertIn("OBJ-1", str(ctx.exception))


class TestAbpWriteAndVerify(unittest.TestCase):
    """Test write_abp and full verify_abp pipeline."""

    def test_write_and_read(self):
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_abp(abp, Path(tmpdir))
            self.assertTrue(path.exists())
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["abp_id"], abp["abp_id"])
            self.assertEqual(loaded["hash"], abp["hash"])

    def test_verify_abp_full(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path, entry_hash = _build_test_ledger(tmpdir)
            auth_ref = {
                "authority_entry_id": "AUTH-aabbccdd",
                "authority_entry_hash": entry_hash,
                "authority_ledger_path": str(ledger_path),
            }
            abp = build_abp(scope=DEMO_SCOPE, authority_ref=auth_ref, clock=FIXED_CLOCK)
            abp_path = write_abp(abp, Path(tmpdir))
            result = verify_abp(abp_path, ledger_path, SCHEMA_PATH)
            for name, ok, detail in result.checks:
                self.assertTrue(ok, f"{name}: {detail}")
            self.assertTrue(result.passed)


class TestVerifyAbpAuthority(unittest.TestCase):
    """Test ABP authority ref verification against ledger."""

    def test_valid_authority(self):
        from build_abp import verify_abp_authority
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path, entry_hash = _build_test_ledger(tmpdir)
            auth_ref = {
                "authority_entry_id": "AUTH-aabbccdd",
                "authority_entry_hash": entry_hash,
                "authority_ledger_path": str(ledger_path),
            }
            abp = build_abp(scope=DEMO_SCOPE, authority_ref=auth_ref, clock=FIXED_CLOCK)
            self.assertTrue(verify_abp_authority(abp, ledger_path))

    def test_revoked_authority(self):
        from build_abp import verify_abp_authority
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path, entry_hash = _build_test_ledger(tmpdir, revoked=True)
            auth_ref = {
                "authority_entry_id": "AUTH-aabbccdd",
                "authority_entry_hash": entry_hash,
                "authority_ledger_path": str(ledger_path),
            }
            abp = build_abp(scope=DEMO_SCOPE, authority_ref=auth_ref, clock=FIXED_CLOCK)
            self.assertFalse(verify_abp_authority(abp, ledger_path))

    def test_missing_authority(self):
        from build_abp import verify_abp_authority
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path, _ = _build_test_ledger(tmpdir)
            auth_ref = {
                "authority_entry_id": "AUTH-00000000",
                "authority_entry_hash": "sha256:0000",
                "authority_ledger_path": str(ledger_path),
            }
            abp = build_abp(scope=DEMO_SCOPE, authority_ref=auth_ref, clock=FIXED_CLOCK)
            self.assertFalse(verify_abp_authority(abp, ledger_path))


class TestAbpSchemaValidation(unittest.TestCase):
    """Test ABP validates against its JSON schema."""

    def test_valid_abp_passes_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        schema = json.loads(SCHEMA_PATH.read_text())
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        jsonschema.validate(abp, schema)

    def test_missing_field_fails_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        schema = json.loads(SCHEMA_PATH.read_text())
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        del abp["scope"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(abp, schema)

    def test_extra_field_fails_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        schema = json.loads(SCHEMA_PATH.read_text())
        abp = build_abp(scope=DEMO_SCOPE, authority_ref=DEMO_AUTH_REF, clock=FIXED_CLOCK)
        abp["rogue_field"] = "should fail"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(abp, schema)


if __name__ == "__main__":
    unittest.main()
