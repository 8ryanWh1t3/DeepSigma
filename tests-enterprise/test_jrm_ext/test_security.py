"""Tests for JRM security — signer and validator."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "enterprise" / "src"))

from deepsigma.jrm_ext.security.signer import PacketSigner
from deepsigma.jrm_ext.security.validator import PacketValidator


class TestPacketSigner:
    def test_sign(self):
        signer = PacketSigner("test-key")
        manifest = {"packetName": "test", "environmentId": "E1"}
        sig = signer.sign(manifest)
        assert sig["algorithm"] == "hmac-sha256"
        assert len(sig["value"]) == 64

    def test_verify(self):
        signer = PacketSigner("test-key")
        manifest = {"packetName": "test", "environmentId": "E1"}
        sig = signer.sign(manifest)
        assert signer.verify(manifest, sig) is True

    def test_verify_wrong_key(self):
        signer1 = PacketSigner("key-a")
        signer2 = PacketSigner("key-b")
        manifest = {"packetName": "test"}
        sig = signer1.sign(manifest)
        assert signer2.verify(manifest, sig) is False

    def test_deterministic(self):
        signer = PacketSigner("key")
        m = {"a": 1, "b": 2}
        assert signer.sign(m)["value"] == signer.sign(m)["value"]


class TestPacketValidator:
    def test_validate_signed_packet(self, tmp_path):
        key = "demo-key"
        signer = PacketSigner(key)

        manifest_data = {
            "packetName": "JRM_X_PACKET_TEST_20260228_part01",
            "environmentId": "TEST",
            "files": {},
            "eventCount": 0,
            "sizeBytes": 0,
        }
        sig = signer.sign(manifest_data)
        manifest_data["signature"] = sig

        zip_path = tmp_path / "signed.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest_data))

        validator = PacketValidator(key)
        assert validator.validate(zip_path) is True

    def test_reject_unsigned(self, tmp_path):
        manifest_data = {"packetName": "test", "files": {}}
        zip_path = tmp_path / "unsigned.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest_data))

        validator = PacketValidator("any-key")
        assert validator.validate(zip_path) is False
