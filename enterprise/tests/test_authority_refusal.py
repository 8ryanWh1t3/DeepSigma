"""Tests for structural refusal authority contract (#414)."""

from __future__ import annotations

import hashlib

from deepsigma.security.action_contract import (
    create_refusal_contract,
    validate_refusal_contract,
)
from deepsigma.security.authority_ledger import (
    append_authority_refusal_entry,
    load_authority_ledger,
)

from core.feeds.consumers.authority_gate import AuthorityGateConsumer


def _make_event(event_id: str = "EVT-REF-001") -> dict:
    return {
        "event_id": event_id,
        "event_hash": hashlib.sha256(event_id.encode()).hexdigest(),
        "tenant_id": "tenant-test",
        "occurred_at": "2026-02-27T00:00:00Z",
        "payload": {},
    }


class TestRefusalContract:
    def test_create_and_validate(self):
        key = "test-signing-key"
        contract = create_refusal_contract(
            refused_action_type="ROTATE_KEYS",
            refused_by="security-officer",
            reason="Rotation window not open",
            dri="dri-admin",
            signing_key=key,
        )
        assert contract.action_type == "REFUSE:ROTATE_KEYS"
        validated = validate_refusal_contract(
            contract.to_dict(),
            refused_action_type="ROTATE_KEYS",
            signing_key=key,
        )
        assert validated.action_type == "REFUSE:ROTATE_KEYS"

    def test_wrong_key_fails(self):
        contract = create_refusal_contract(
            refused_action_type="ROTATE_KEYS",
            refused_by="officer",
            reason="no",
            dri="dri",
            signing_key="key-1",
        )
        try:
            validate_refusal_contract(
                contract.to_dict(),
                refused_action_type="ROTATE_KEYS",
                signing_key="key-2",
            )
            assert False, "Should have raised"
        except ValueError:
            pass


class TestRefusalLedgerEntry:
    def test_append_refusal(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        entry = append_authority_refusal_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            refused_by="security-officer",
            refused_action_type="ROTATE_KEYS",
            refusal_reason="Key rotation window closed",
            signing_key="test-key",
        )
        assert entry["entry_type"] == "AUTHORITY_REFUSAL"
        assert entry["refused_by"] == "security-officer"
        assert entry["refused_action_type"] == "ROTATE_KEYS"
        assert entry["refusal_reason"] == "Key rotation window closed"
        assert entry["entry_id"].startswith("AUTHREF-")

    def test_refusal_in_loaded_ledger(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        append_authority_refusal_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            refused_by="officer",
            refused_action_type="REENCRYPT",
            refusal_reason="Not authorized",
            signing_key="key",
        )
        entries = load_authority_ledger(ledger)
        assert len(entries) == 1
        assert entries[0]["entry_type"] == "AUTHORITY_REFUSAL"


class TestAuthorityGateRefusal:
    def test_refused_action_emits_drift(self):
        gate = AuthorityGateConsumer()
        dlr = {
            "dlrId": "DLR-001",
            "claims": {"action": [{"claimId": "ROTATE_KEYS"}]},
        }
        refusals = [
            {"entry_type": "AUTHORITY_REFUSAL", "refused_action_type": "ROTATE_KEYS"},
        ]
        result = gate.check_refusals(dlr, refusals)
        assert result is not None
        assert result["driftType"] == "authority_refused"
        assert result["severity"] == "red"

    def test_no_refusal_returns_none(self):
        gate = AuthorityGateConsumer()
        dlr = {
            "dlrId": "DLR-001",
            "claims": {"action": [{"claimId": "ROTATE_KEYS"}]},
        }
        result = gate.check_refusals(dlr, [])
        assert result is None

    def test_unmatched_refusal_returns_none(self):
        gate = AuthorityGateConsumer()
        dlr = {
            "dlrId": "DLR-001",
            "claims": {"action": [{"claimId": "SEAL_EPISODE"}]},
        }
        refusals = [
            {"entry_type": "AUTHORITY_REFUSAL", "refused_action_type": "ROTATE_KEYS"},
        ]
        result = gate.check_refusals(dlr, refusals)
        assert result is None
