"""Tests for JRM Gate."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "enterprise" / "src"))

from deepsigma.jrm_ext.federation.gate import JRMGate


class TestGate:
    def test_valid_packet(self, make_packet):
        gate = JRMGate()
        result = gate.validate(make_packet())
        assert result.accepted is True
        assert result.violations == []

    def test_missing_file(self, tmp_path, make_packet):
        # Create a packet and remove a file
        packet = make_packet()
        bad_zip = tmp_path / "bad.zip"
        with zipfile.ZipFile(packet, "r") as zf_in, \
             zipfile.ZipFile(bad_zip, "w") as zf_out:
            for name in zf_in.namelist():
                if name != "truth_snapshot.json":
                    zf_out.writestr(name, zf_in.read(name))

        gate = JRMGate()
        result = gate.validate(bad_zip)
        assert result.accepted is False
        assert any("truth_snapshot.json" in v for v in result.violations)

    def test_hash_mismatch(self, tmp_path, make_packet):
        packet = make_packet()
        bad_zip = tmp_path / "tampered.zip"
        with zipfile.ZipFile(packet, "r") as zf_in, \
             zipfile.ZipFile(bad_zip, "w") as zf_out:
            for name in zf_in.namelist():
                content = zf_in.read(name)
                if name == "truth_snapshot.json":
                    content = b'{"tampered": true}'
                zf_out.writestr(name, content)

        gate = JRMGate()
        result = gate.validate(bad_zip)
        assert result.accepted is False
        assert any("Hash mismatch" in v for v in result.violations)

    def test_scope_enforcement(self, make_packet):
        gate = JRMGate()
        packet = make_packet(env="SOC_EAST")

        ok = gate.enforce_scope(packet, allowed_envs={"SOC_EAST", "SOC_WEST"})
        assert ok.accepted is True

        blocked = gate.enforce_scope(packet, allowed_envs={"SOC_WEST"})
        assert blocked.accepted is False
        assert blocked.reason_code == "SCOPE_VIOLATION"

    def test_nonexistent_packet(self):
        gate = JRMGate()
        result = gate.validate("/nonexistent/path.zip")
        assert result.accepted is False
        assert result.reason_code == "NOT_FOUND"

    def test_redact(self, tmp_path, make_packet):
        packet = make_packet()
        gate = JRMGate()
        redacted = gate.redact(packet, redact_fields=["environmentId"])
        assert redacted.exists()
        with zipfile.ZipFile(redacted, "r") as zf:
            ce = json.loads(zf.read("canon_entry.json"))
            assert ce.get("environmentId") == "[REDACTED]"
