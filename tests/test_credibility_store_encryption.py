from __future__ import annotations

import json

import pytest

from credibility_engine.store import CredibilityStore

pytest.importorskip("cryptography.hazmat.primitives.ciphers.aead")


def test_encrypt_at_rest_jsonl_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "current-master-key")
    store = CredibilityStore(
        data_dir=tmp_path,
        tenant_id="alpha",
        encrypt_at_rest=True,
    )
    store.append_claim({"claim_id": "C-1", "score": 0.9})

    raw = (tmp_path / "claims.jsonl").read_text(encoding="utf-8").strip()
    assert "encrypted_payload" in raw
    assert "claim_id" not in raw

    records = store.latest_claims()
    assert len(records) == 1
    assert records[0]["claim_id"] == "C-1"
    assert records[0]["tenant_id"] == "alpha"


def test_packet_remains_plaintext(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "current-master-key")
    store = CredibilityStore(
        data_dir=tmp_path,
        tenant_id="alpha",
        encrypt_at_rest=True,
    )
    packet = {"packet_id": "PKT-1", "status": "ok"}
    store.save_packet(packet)
    raw = json.loads((tmp_path / "packet_latest.json").read_text(encoding="utf-8"))
    assert raw["packet_id"] == "PKT-1"
    assert "encrypted_payload" not in raw


def test_rekey_reencrypts_records(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "old-master-key")
    old_store = CredibilityStore(
        data_dir=tmp_path,
        tenant_id="alpha",
        encrypt_at_rest=True,
    )
    old_store.append_claim({"claim_id": "C-1", "score": 0.9})

    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "new-master-key")
    new_store = CredibilityStore(
        data_dir=tmp_path,
        tenant_id="alpha",
        encrypt_at_rest=True,
    )
    stats = new_store.rekey(previous_master_key="old-master-key")
    assert stats["records"] >= 1

    # New key reads successfully.
    after = new_store.latest_claims()
    assert after[0]["claim_id"] == "C-1"

    # Old key can no longer decrypt after rotation.
    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "old-master-key")
    stale_store = CredibilityStore(
        data_dir=tmp_path,
        tenant_id="alpha",
        encrypt_at_rest=True,
    )
    try:
        stale_store.latest_claims()
        assert False, "Expected decrypt failure with old key"
    except Exception:
        pass
