"""Tests for authority ledger append + verify tools."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools" / "reconstruct"))

from authority_ledger_append import (  # noqa: E402
    append_entry,
    find_active_for_actor,
    find_entry,
    revoke_entry,
    verify_chain,
)
from authority_ledger_verify import verify_ledger  # noqa: E402

FIXED_CLOCK = "2026-02-21T00:00:00Z"


class AuthorityLedgerTestBase(unittest.TestCase):
    """Base class with tmpdir + ledger path."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = Path(self.tmpdir) / "ledger.ndjson"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestAppendFirstEntry(AuthorityLedgerTestBase):
    def test_append_first_entry(self) -> None:
        entry = append_entry(
            self.ledger,
            authority_id="GOV-1",
            actor_id="alice",
            actor_role="Operator",
            grant_type="direct",
            effective_at=FIXED_CLOCK,
            policy_version="GOV-2.0.2",
            policy_hash="sha256:abc",
        )
        self.assertTrue(entry["entry_id"].startswith("AUTH-"))
        self.assertEqual(len(entry["entry_id"]), 13)  # AUTH-xxxxxxxx
        self.assertIsNone(entry["prev_entry_hash"])
        self.assertTrue(entry["entry_hash"].startswith("sha256:"))
        self.assertEqual(entry["authority_id"], "GOV-1")
        self.assertEqual(entry["actor_id"], "alice")
        self.assertEqual(entry["grant_type"], "direct")
        self.assertTrue(self.ledger.exists())


class TestAppendSecondEntry(AuthorityLedgerTestBase):
    def test_chaining(self) -> None:
        e1 = append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        e2 = append_entry(
            self.ledger, "GOV-2", "bob", "Reviewer", "delegated",
            effective_at="2026-02-21T01:00:00Z",
        )
        self.assertIsNone(e1["prev_entry_hash"])
        self.assertEqual(e2["prev_entry_hash"], e1["entry_hash"])
        self.assertNotEqual(e1["entry_hash"], e2["entry_hash"])


class TestEntryHashIntegrity(AuthorityLedgerTestBase):
    def test_recompute_hash(self) -> None:
        from canonical_json import canonical_dumps, sha256_text

        entry = append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        # Recompute from scratch
        copy = dict(entry)
        copy["entry_hash"] = ""
        expected = sha256_text(canonical_dumps(copy))
        self.assertEqual(entry["entry_hash"], expected)


class TestVerifyChainValid(AuthorityLedgerTestBase):
    def test_multi_entry_chain(self) -> None:
        for i in range(5):
            append_entry(
                self.ledger, f"GOV-{i}", f"actor-{i}", "Operator", "direct",
                effective_at=f"2026-02-21T0{i}:00:00Z",
            )
        results = verify_chain(self.ledger)
        self.assertTrue(all(ok for _, ok, _ in results))
        # 5 entries × 2 checks each (hash + chain) = 10
        self.assertEqual(len(results), 10)


class TestVerifyChainTampered(AuthorityLedgerTestBase):
    def test_tampered_hash_detected(self) -> None:
        for i in range(3):
            append_entry(
                self.ledger, f"GOV-{i}", f"actor-{i}", "Operator", "direct",
                effective_at=f"2026-02-21T0{i}:00:00Z",
            )
        # Tamper with middle entry
        lines = self.ledger.read_text().strip().split("\n")
        entry = json.loads(lines[1])
        entry["actor_id"] = "TAMPERED"
        lines[1] = json.dumps(entry, sort_keys=True)
        self.ledger.write_text("\n".join(lines) + "\n")

        results = verify_chain(self.ledger)
        failed = [r for r in results if not r[1]]
        self.assertGreater(len(failed), 0)


class TestRevokeEntry(AuthorityLedgerTestBase):
    def test_revocation_appended(self) -> None:
        append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        rev = revoke_entry(
            self.ledger, "GOV-1", "Policy expired",
            clock="2026-02-21T12:00:00Z",
        )
        self.assertEqual(rev["grant_type"], "revocation")
        self.assertEqual(rev["revoked_at"], "2026-02-21T12:00:00Z")
        self.assertEqual(rev["revocation_reason"], "Policy expired")
        self.assertEqual(rev["authority_id"], "GOV-1")

    def test_revoke_nonexistent_raises(self) -> None:
        append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        with self.assertRaises(ValueError):
            revoke_entry(self.ledger, "GOV-NOPE", "reason")


class TestFindActiveForActor(AuthorityLedgerTestBase):
    def test_filters_by_time_and_revocation(self) -> None:
        # Grant at T0
        append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at="2026-02-21T00:00:00Z",
        )
        # Grant at T1 (expires at T3)
        append_entry(
            self.ledger, "GOV-2", "alice", "Operator", "direct",
            effective_at="2026-02-21T01:00:00Z",
            expires_at="2026-02-21T03:00:00Z",
        )
        # Revoke GOV-1 at T2
        revoke_entry(
            self.ledger, "GOV-1", "Revoked",
            clock="2026-02-21T02:00:00Z",
        )

        # At T0:30 — both active
        active = find_active_for_actor(self.ledger, "alice", "2026-02-21T01:30:00Z")
        auth_ids = {e["authority_id"] for e in active}
        self.assertIn("GOV-1", auth_ids)
        self.assertIn("GOV-2", auth_ids)

        # At T2:30 — GOV-1 revoked, GOV-2 still active
        active = find_active_for_actor(self.ledger, "alice", "2026-02-21T02:30:00Z")
        auth_ids = {e["authority_id"] for e in active}
        self.assertNotIn("GOV-1", auth_ids)
        self.assertIn("GOV-2", auth_ids)

        # At T4 — GOV-1 revoked, GOV-2 expired
        active = find_active_for_actor(self.ledger, "alice", "2026-02-21T04:00:00Z")
        self.assertEqual(len(active), 0)


class TestFindEntry(AuthorityLedgerTestBase):
    def test_find_by_id(self) -> None:
        e1 = append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        found = find_entry(self.ledger, e1["entry_id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["entry_id"], e1["entry_id"])

    def test_not_found(self) -> None:
        append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        self.assertIsNone(find_entry(self.ledger, "AUTH-00000000"))


class TestScopeBound(AuthorityLedgerTestBase):
    def test_custom_scope(self) -> None:
        scope = {
            "decisions": ["DEC-001", "DEC-002"],
            "claims": ["CLM-001"],
            "patches": [],
            "prompts": [],
            "datasets": [],
        }
        entry = append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            scope_bound=scope,
            effective_at=FIXED_CLOCK,
        )
        self.assertEqual(entry["scope_bound"]["decisions"], ["DEC-001", "DEC-002"])
        self.assertEqual(entry["scope_bound"]["claims"], ["CLM-001"])

    def test_default_scope(self) -> None:
        entry = append_entry(
            self.ledger, "GOV-1", "alice", "Operator", "direct",
            effective_at=FIXED_CLOCK,
        )
        for key in ("decisions", "claims", "patches", "prompts", "datasets"):
            self.assertIn(key, entry["scope_bound"])


class TestVerifyLedger(AuthorityLedgerTestBase):
    def test_valid_ledger(self) -> None:
        for i in range(3):
            append_entry(
                self.ledger, f"GOV-{i}", f"actor-{i}", "Operator", "direct",
                effective_at=f"2026-02-21T0{i}:00:00Z",
            )
        result = verify_ledger(self.ledger)
        self.assertTrue(result.passed)
        self.assertEqual(result.failed_count, 0)

    def test_tampered_ledger(self) -> None:
        for i in range(3):
            append_entry(
                self.ledger, f"GOV-{i}", f"actor-{i}", "Operator", "direct",
                effective_at=f"2026-02-21T0{i}:00:00Z",
            )
        # Tamper
        lines = self.ledger.read_text().strip().split("\n")
        entry = json.loads(lines[1])
        entry["actor_id"] = "TAMPERED"
        lines[1] = json.dumps(entry, sort_keys=True)
        self.ledger.write_text("\n".join(lines) + "\n")

        result = verify_ledger(self.ledger)
        self.assertFalse(result.passed)
        self.assertGreater(result.failed_count, 0)

    def test_missing_file(self) -> None:
        result = verify_ledger(Path("/nonexistent/ledger.ndjson"))
        self.assertFalse(result.passed)

    def test_empty_ledger(self) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("")
        result = verify_ledger(self.ledger)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
