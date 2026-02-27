"""Tests for the core AuthorityLedger module."""

import json
from pathlib import Path

import pytest

from core.authority import AuthorityEntry, AuthorityLedger


def _make_grant(claims=None, source="governance-engine", role="policy-owner",
                scope="security-ops"):
    return AuthorityEntry(
        entry_id="",
        entry_type="grant",
        authority_source=source,
        authority_role=role,
        scope=scope,
        claims_blessed=claims or ["CLAIM-2026-0001"],
        effective_at="2026-02-27T10:00:00Z",
        expires_at=None,
        entry_hash="",
        prev_entry_hash=None,
    )


def _make_revocation(claims=None):
    return AuthorityEntry(
        entry_id="",
        entry_type="revocation",
        authority_source="governance-engine",
        authority_role="policy-owner",
        scope="security-ops",
        claims_blessed=claims or ["CLAIM-2026-0001"],
        effective_at="2026-02-27T12:00:00Z",
        expires_at=None,
        entry_hash="",
        prev_entry_hash=None,
    )


# ── Append ──────────────────────────────────────────────────────


class TestAuthorityLedgerAppend:
    def test_append_returns_hash(self):
        ledger = AuthorityLedger()
        h = ledger.append(_make_grant())
        assert h.startswith("sha256:")

    def test_append_sets_entry_id(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        assert ledger.entries[0].entry_id.startswith("AUTH-")

    def test_append_first_has_no_prev(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        assert ledger.entries[0].prev_entry_hash is None

    def test_append_second_chains_to_first(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        ledger.append(_make_grant(claims=["CLAIM-2026-0002"]))
        assert (
            ledger.entries[1].prev_entry_hash == ledger.entries[0].entry_hash
        )

    def test_append_sets_recorded_at(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        assert ledger.entries[0].recorded_at != ""

    def test_entry_count(self):
        ledger = AuthorityLedger()
        assert ledger.entry_count == 0
        ledger.append(_make_grant())
        assert ledger.entry_count == 1
        ledger.append(_make_grant())
        assert ledger.entry_count == 2


# ── Verify Chain ────────────────────────────────────────────────


class TestAuthorityLedgerVerify:
    def test_empty_ledger_is_valid(self):
        ledger = AuthorityLedger()
        assert ledger.verify_chain() is True

    def test_single_entry_valid(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        assert ledger.verify_chain() is True

    def test_chain_of_three_valid(self):
        ledger = AuthorityLedger()
        for i in range(3):
            ledger.append(_make_grant(claims=[f"CLAIM-{i}"]))
        assert ledger.verify_chain() is True

    def test_tampered_hash_detected(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        ledger._entries[0].entry_hash = "sha256:tampered"
        assert ledger.verify_chain() is False

    def test_broken_chain_link_detected(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        ledger.append(_make_grant(claims=["CLAIM-2"]))
        ledger._entries[1].prev_entry_hash = "sha256:wrong"
        assert ledger.verify_chain() is False


# ── Prove Authority ─────────────────────────────────────────────


class TestAuthorityLedgerProve:
    def test_prove_granted_claim(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"]))
        proof = ledger.prove_authority("CLAIM-A")
        assert proof is not None
        assert proof["claim_id"] == "CLAIM-A"
        assert "entry_id" in proof
        assert proof["chain_valid"] is True

    def test_prove_unknown_claim(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"]))
        assert ledger.prove_authority("CLAIM-UNKNOWN") is None

    def test_prove_revoked_claim(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"]))
        ledger.append(_make_revocation(claims=["CLAIM-A"]))
        assert ledger.prove_authority("CLAIM-A") is None

    def test_prove_uses_latest_grant(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"], source="old-source"))
        ledger.append(_make_grant(claims=["CLAIM-A"], source="new-source"))
        proof = ledger.prove_authority("CLAIM-A")
        assert proof["authority_source"] == "new-source"

    def test_prove_includes_entry_hash(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"]))
        proof = ledger.prove_authority("CLAIM-A")
        assert proof["entry_hash"].startswith("sha256:")


# ── Snapshot ────────────────────────────────────────────────────


class TestAuthorityLedgerSnapshot:
    def test_snapshot_returns_dict(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        snap = ledger.snapshot()
        assert "schema_version" in snap
        assert "entry_count" in snap
        assert "ledger_hash" in snap

    def test_snapshot_entry_count_matches(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant())
        ledger.append(_make_grant())
        snap = ledger.snapshot()
        assert snap["entry_count"] == 2


# ── Authority Slice ─────────────────────────────────────────────


class TestAuthorityLedgerALS:
    def test_to_authority_slice_format(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A"]))
        als = ledger.to_authority_slice()
        assert "sliceId" in als
        assert "claimsBlessed" in als
        assert "seal" in als
        assert "CLAIM-A" in als["claimsBlessed"]

    def test_als_reflects_grants_minus_revocations(self):
        ledger = AuthorityLedger()
        ledger.append(_make_grant(claims=["CLAIM-A", "CLAIM-B"]))
        ledger.append(_make_revocation(claims=["CLAIM-A"]))
        als = ledger.to_authority_slice()
        assert "CLAIM-B" in als["claimsBlessed"]
        assert "CLAIM-A" not in als["claimsBlessed"]


# ── Persistence ─────────────────────────────────────────────────


class TestAuthorityLedgerPersistence:
    def test_persist_and_reload(self, tmp_path):
        p = tmp_path / "ledger.json"
        ledger1 = AuthorityLedger(path=p)
        ledger1.append(_make_grant(claims=["CLAIM-X"]))
        ledger1.append(_make_grant(claims=["CLAIM-Y"]))

        ledger2 = AuthorityLedger(path=p)
        assert ledger2.entry_count == 2
        assert ledger2.verify_chain() is True
        assert ledger2.entries[0].claims_blessed == ["CLAIM-X"]

    def test_empty_file_loads_empty(self, tmp_path):
        p = tmp_path / "ledger.json"
        p.write_text("")
        ledger = AuthorityLedger(path=p)
        assert ledger.entry_count == 0

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "ledger.json"
        p.write_text('{"not": "an array"}')
        with pytest.raises(ValueError, match="JSON array"):
            AuthorityLedger(path=p)
