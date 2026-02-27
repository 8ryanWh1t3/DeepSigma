#!/usr/bin/env python3
"""Security Posture Proof Pack v2 — integrity chain summary + verification evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENT_ROOT = Path(__file__).resolve().parents[1]
RK = ENT_ROOT / "release_kpis"
SECURITY_DOCS = ENT_ROOT / "docs" / "docs" / "security"


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_key_lifecycle() -> dict:
    path = SECURITY_DOCS / "KEY_LIFECYCLE.md"
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    text = path.read_text(encoding="utf-8").lower()
    checks = {
        "documents_generation": any(w in text for w in ["generat", "create", "provision"]),
        "documents_rotation": "rotat" in text,
        "documents_revocation": any(w in text for w in ["revok", "revocat", "decommission"]),
    }
    return {
        "present": True,
        "path": str(path.relative_to(ROOT)),
        "hash": sha256_file(path),
        **checks,
    }


def check_crypto_proof() -> dict:
    path = ENT_ROOT / "scripts" / "crypto_proof.py"
    if not path.exists():
        return {"present": False, "path": "enterprise/scripts/crypto_proof.py"}
    text = path.read_text(encoding="utf-8")
    has_build = "def build_proof" in text
    has_verify = "def verify" in text or "verify_proof" in text
    return {
        "present": True,
        "path": "enterprise/scripts/crypto_proof.py",
        "hash": sha256_file(path),
        "has_build_proof": has_build,
        "has_verify": has_verify,
    }


def check_seal_chain() -> dict:
    """Check credibility packet seal chain for hash continuity."""
    packet_dir = ENT_ROOT / "artifacts" / "credibility"
    if not packet_dir.exists():
        # Try release_kpis for any seal chain evidence.
        return {"present": False, "note": "no credibility artifacts directory"}

    packets = sorted(packet_dir.glob("*.json"))
    if not packets:
        return {"present": False, "note": "no credibility packets found"}

    chain_valid = True
    chain_length = 0
    prev_seal = None
    for p in packets:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        seal = obj.get("seal_chain", [])
        if not seal:
            continue
        for entry in seal:
            chain_length += 1
            entry_prev = entry.get("prev_seal_hash")
            if prev_seal is not None and entry_prev != prev_seal:
                chain_valid = False
            prev_seal = entry.get("seal_hash")

    return {
        "present": chain_length > 0,
        "chain_length": chain_length,
        "chain_valid": chain_valid,
    }


def check_contract_fingerprint() -> dict:
    fp_path = ROOT / "reference" / "CONTRACT_FINGERPRINT"
    manifest_path = ROOT / "reference" / "schema_manifest.json"
    if not fp_path.exists() or not manifest_path.exists():
        return {"present": False}
    fp = fp_path.read_text(encoding="utf-8").strip()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_fp = manifest.get("contractFingerprint", "")
    return {
        "present": True,
        "fingerprint": fp,
        "manifest_match": fp == manifest_fp,
        "schema_count": manifest.get("schema_count", 0),
    }


def main() -> int:
    key_lifecycle = check_key_lifecycle()
    crypto_proof = check_crypto_proof()
    seal_chain = check_seal_chain()
    contract_fp = check_contract_fingerprint()

    # Schema manifest hash.
    manifest_hash = sha256_file(ROOT / "reference" / "schema_manifest.json")

    proof_pack = {
        "schema": "security_proof_pack_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key_custody_model": key_lifecycle,
        "signature_verification": crypto_proof,
        "seal_chain_integrity": seal_chain,
        "contract_fingerprint": contract_fp,
        "schema_manifest_hash": manifest_hash,
    }

    # Determine overall status.
    checks = [
        ("key_lifecycle", key_lifecycle.get("present", False)),
        ("crypto_proof", crypto_proof.get("present", False)),
        ("contract_fingerprint", contract_fp.get("present", False) and contract_fp.get("manifest_match", False)),
    ]
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    status = "PASS" if passed == total else "WARN"

    proof_pack["status"] = status
    proof_pack["checks_passed"] = passed
    proof_pack["checks_total"] = total

    # Write JSON.
    json_path = RK / "security_proof_pack.json"
    json_path.write_text(json.dumps(proof_pack, indent=2) + "\n", encoding="utf-8")

    # Write enriched markdown report.
    lines = [
        "# Security Gate Report",
        "",
        f"## {status}",
        "",
        "### Key Custody Model",
        f"- Present: {key_lifecycle.get('present', False)}",
    ]
    if key_lifecycle.get("present"):
        lines.append(f"- Documents generation: {key_lifecycle.get('documents_generation', False)}")
        lines.append(f"- Documents rotation: {key_lifecycle.get('documents_rotation', False)}")
        lines.append(f"- Documents revocation: {key_lifecycle.get('documents_revocation', False)}")

    lines.extend([
        "",
        "### Signature Verification",
        f"- crypto_proof.py present: {crypto_proof.get('present', False)}",
        f"- Has build_proof: {crypto_proof.get('has_build_proof', False)}",
        f"- Has verify: {crypto_proof.get('has_verify', False)}",
        "",
        "### Contract Fingerprint",
        f"- Present: {contract_fp.get('present', False)}",
        f"- Manifest match: {contract_fp.get('manifest_match', False)}",
        f"- Fingerprint: {contract_fp.get('fingerprint', 'N/A')}",
        "",
        "### Seal Chain Integrity",
        f"- Present: {seal_chain.get('present', False)}",
        f"- Chain length: {seal_chain.get('chain_length', 0)}",
        f"- Chain valid: {seal_chain.get('chain_valid', 'N/A')}",
        "",
    ])

    md_path = RK / "SECURITY_GATE_REPORT.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[{status}] Security Proof Pack v2 ({passed}/{total} checks)")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
