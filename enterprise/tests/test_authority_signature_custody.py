"""Tests for authority signature key custody and verification path (#413)."""

from __future__ import annotations

import hmac
import hashlib
import json

from deepsigma.security.authority_ledger import (
    append_authority_action_entry,
    load_authority_ledger,
    _event_signature,
    _canonical_json,
)


def _make_event(event_id: str = "EVT-001") -> dict:
    return {
        "event_id": event_id,
        "event_hash": hashlib.sha256(event_id.encode()).hexdigest(),
        "tenant_id": "tenant-test",
        "occurred_at": "2026-02-27T00:00:00Z",
        "payload": {"key_id": "k1", "key_version": "v1"},
    }


class TestSignVerify:
    def test_sign_and_verify(self):
        key = "test-signing-key-32bytes-long!!"
        payload = {"action": "rotate", "key_id": "k1"}
        sig = _event_signature(payload, key)
        expected = hmac.new(
            key.encode(), _canonical_json(payload).encode(), hashlib.sha256
        ).hexdigest()
        assert sig == expected

    def test_tampered_message_fails(self):
        key = "test-signing-key-32bytes-long!!"
        payload = {"action": "rotate", "key_id": "k1"}
        sig = _event_signature(payload, key)
        tampered = {"action": "rotate", "key_id": "k2"}
        tampered_sig = _event_signature(tampered, key)
        assert sig != tampered_sig

    def test_wrong_key_fails(self):
        payload = {"action": "rotate", "key_id": "k1"}
        sig1 = _event_signature(payload, "key-one")
        sig2 = _event_signature(payload, "key-two")
        assert sig1 != sig2


class TestSigningKeyId:
    def test_default_signing_key_id(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        entry = append_authority_action_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            authority_dri="admin",
            authority_role="dri",
            authority_reason="test",
            signing_key="test-key",
            action_type="TEST_ACTION",
        )
        assert entry["signing_key_id"] == "default"

    def test_custom_signing_key_id(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        entry = append_authority_action_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            authority_dri="admin",
            authority_role="dri",
            authority_reason="test",
            signing_key="test-key",
            action_type="TEST_ACTION",
            signing_key_id="rotation-2026-q1",
        )
        assert entry["signing_key_id"] == "rotation-2026-q1"

    def test_signing_key_id_in_loaded_ledger(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        append_authority_action_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            authority_dri="admin",
            authority_role="dri",
            authority_reason="test",
            signing_key="test-key",
            action_type="TEST_ACTION",
            signing_key_id="my-key-id",
        )
        entries = load_authority_ledger(ledger)
        assert len(entries) == 1
        assert entries[0]["signing_key_id"] == "my-key-id"


class TestMissingKey:
    def test_empty_signing_key_produces_signature(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        # Empty key still produces a valid HMAC (this is by design —
        # the caller is responsible for providing a real key)
        entry = append_authority_action_entry(
            ledger_path=ledger,
            authority_event=_make_event(),
            authority_dri="admin",
            authority_role="dri",
            authority_reason="test",
            signing_key="",
            action_type="TEST_ACTION",
        )
        assert entry["event_signature"]
        assert entry["signature_alg"] == "HMAC-SHA256"
