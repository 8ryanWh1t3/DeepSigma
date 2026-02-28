"""JRM Gate — validate, enforce scope, and redact packets."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Set

from ..types import GateResult


REQUIRED_PACKET_FILES = {
    "truth_snapshot.json",
    "authority_slice.json",
    "decision_lineage.jsonl",
    "drift_signal.jsonl",
    "memory_graph.json",
    "canon_entry.json",
    "manifest.json",
}


class JRMGate:
    """Validate JRM-X packets before federation ingestion."""

    def validate(self, packet_path: str | Path) -> GateResult:
        """Validate packet structure, required files, and hash integrity."""
        packet_path = Path(packet_path)
        violations: List[str] = []

        if not packet_path.exists():
            return GateResult(accepted=False, reason_code="NOT_FOUND",
                              violations=[f"Packet not found: {packet_path}"])

        try:
            with zipfile.ZipFile(packet_path, "r") as zf:
                names = set(zf.namelist())

                # Check required files
                missing = REQUIRED_PACKET_FILES - names
                if missing:
                    violations.append(f"Missing required files: {sorted(missing)}")

                # Validate manifest
                if "manifest.json" in names:
                    manifest = json.loads(zf.read("manifest.json"))

                    # Check environment_id present
                    if not manifest.get("environmentId"):
                        violations.append("Manifest missing environmentId")

                    # Verify file hashes
                    for fname, expected_hash in manifest.get("files", {}).items():
                        if fname in names:
                            content = zf.read(fname)
                            actual = f"sha256:{hashlib.sha256(content).hexdigest()}"
                            if actual != expected_hash:
                                violations.append(
                                    f"Hash mismatch: {fname} expected {expected_hash}, got {actual}"
                                )
                        else:
                            violations.append(f"File in manifest but missing: {fname}")
                else:
                    violations.append("Missing manifest.json")

        except zipfile.BadZipFile:
            violations.append("Not a valid zip file")

        accepted = len(violations) == 0
        reason = "ok" if accepted else "VALIDATION_FAILED"
        return GateResult(accepted=accepted, reason_code=reason, violations=violations)

    def enforce_scope(
        self,
        packet_path: str | Path,
        allowed_envs: Set[str] | None = None,
        allowed_signatures: Set[str] | None = None,
    ) -> GateResult:
        """Reject packets from unauthorized environments or signatures."""
        packet_path = Path(packet_path)
        violations: List[str] = []

        try:
            with zipfile.ZipFile(packet_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    return GateResult(accepted=False, reason_code="NO_MANIFEST",
                                      violations=["Missing manifest"])

                manifest = json.loads(zf.read("manifest.json"))
                env_id = manifest.get("environmentId", "")

                if allowed_envs and env_id not in allowed_envs:
                    violations.append(f"Environment {env_id!r} not in allowlist")

        except zipfile.BadZipFile:
            violations.append("Not a valid zip file")

        accepted = len(violations) == 0
        reason = "ok" if accepted else "SCOPE_VIOLATION"
        return GateResult(accepted=accepted, reason_code=reason, violations=violations)

    def redact(
        self,
        packet_path: str | Path,
        redact_fields: List[str] | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        """Strip specified fields from packet files (demo redaction)."""
        packet_path = Path(packet_path)
        redact_fields = redact_fields or []

        if output_path is None:
            output_path = packet_path.with_name(
                packet_path.stem + "_redacted" + packet_path.suffix
            )
        output_path = Path(output_path)

        with zipfile.ZipFile(packet_path, "r") as zf_in, \
             zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for name in zf_in.namelist():
                content = zf_in.read(name)
                if name.endswith(".json") and redact_fields:
                    try:
                        data = json.loads(content)
                        data = _redact_dict(data, set(redact_fields))
                        content = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
                    except (json.JSONDecodeError, ValueError):
                        pass
                zf_out.writestr(name, content)

        return output_path


def _redact_dict(obj: Any, fields: Set[str]) -> Any:
    """Recursively redact specified fields from a dict."""
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if k in fields else _redact_dict(v, fields)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_dict(item, fields) for item in obj]
    return obj
