#!/usr/bin/env python3
"""Sign a sealed governance artifact (sealed run or manifest).

Supports two algorithms:
  - ed25519 (preferred): requires pynacl or cryptography
  - hmac-sha256 (fallback): Python standard library only

Usage:
    # HMAC (stdlib)
    python src/tools/reconstruct/sign_artifact.py \\
        --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \\
        --algo hmac \\
        --key-id ds-dev-2026-02 \\
        --key "$DEEPSIGMA_SIGNING_KEY"

    # Ed25519
    python src/tools/reconstruct/sign_artifact.py \\
        --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \\
        --algo ed25519 \\
        --key-id ds-prod-2026-02 \\
        --key "$DEEPSIGMA_SIGNING_KEY"
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_bytes
from time_controls import observed_now


# ── Ed25519 support (optional dependency) ────────────────────────
def _try_import_ed25519():
    """Try to import ed25519 signing from available libraries."""
    try:
        from nacl.signing import SigningKey  # pynacl
        return "pynacl", SigningKey
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        return "cryptography", Ed25519PrivateKey
    except ImportError:
        pass
    return None, None


# ── Signing implementations ──────────────────────────────────────
def sign_hmac(payload_bytes: bytes, key_b64: str) -> str:
    """Sign with HMAC-SHA256. Returns base64 signature."""
    key = base64.b64decode(key_b64)
    sig = hmac.new(key, payload_bytes, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def sign_ed25519(payload_bytes: bytes, key_b64: str) -> tuple[str, str]:
    """Sign with Ed25519. Returns (base64 signature, base64 public key)."""
    lib, cls = _try_import_ed25519()
    if lib is None:
        print("ERROR: Ed25519 requires pynacl or cryptography. Install with:", file=sys.stderr)
        print("  pip install pynacl", file=sys.stderr)
        sys.exit(1)

    key_bytes = base64.b64decode(key_b64)

    if lib == "pynacl":
        from nacl.signing import SigningKey
        sk = SigningKey(key_bytes)
        signed = sk.sign(payload_bytes)
        sig_b64 = base64.b64encode(signed.signature).decode()
        pub_b64 = base64.b64encode(sk.verify_key.encode()).decode()
        return sig_b64, pub_b64
    else:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )
        sk = Ed25519PrivateKey.from_private_bytes(key_bytes)
        sig = sk.sign(payload_bytes)
        sig_b64 = base64.b64encode(sig).decode()
        pub_bytes = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        pub_b64 = base64.b64encode(pub_bytes).decode()
        return sig_b64, pub_b64


# ── Builder ──────────────────────────────────────────────────────
def build_signature_block(
    artifact_path: Path,
    algorithm: str,
    key_id: str,
    key_b64: str,
    signer_id: str | None = None,
    role: str | None = None,
    signer_type: str | None = None,
) -> dict:
    """Build a signature block for a sealed artifact."""
    raw_bytes = artifact_path.read_bytes()

    # Parse to extract commit_hash and compute canonical bytes hash
    artifact = json.loads(raw_bytes)
    commit_hash = artifact.get("commit_hash", "")

    # If this is a manifest, get commit_hash from there
    if not commit_hash and "commit_hash" in artifact:
        commit_hash = artifact["commit_hash"]

    # Compute hash of the canonical JSON bytes
    canonical_bytes = canonical_dumps(artifact).encode("utf-8")
    payload_bytes_hash = sha256_bytes(canonical_bytes)

    # Determine payload type
    name = artifact_path.name
    if ".manifest." in name:
        payload_type = "manifest"
    else:
        payload_type = "sealed_run"

    # Sign the canonical bytes
    public_key = None
    if algorithm == "hmac-sha256" or algorithm == "hmac":
        signature = sign_hmac(canonical_bytes, key_b64)
        verification_instructions = (
            "Verify with: python src/tools/reconstruct/verify_signature.py "
            f"--file {artifact_path} --sig {artifact_path}.sig.json --key <shared-key-b64>"
        )
    elif algorithm == "ed25519":
        signature, public_key = sign_ed25519(canonical_bytes, key_b64)
        verification_instructions = (
            "Verify with: python src/tools/reconstruct/verify_signature.py "
            f"--file {artifact_path} --sig {artifact_path}.sig.json --public-key <pub-key-b64>"
        )
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Normalize algorithm name
    algo_name = "hmac-sha256" if algorithm in ("hmac", "hmac-sha256") else algorithm

    block = {
        "sig_version": "1.0",
        "algorithm": algo_name,
        "signing_key_id": key_id,
        "signed_at": observed_now(),
        "payload_type": payload_type,
        "payload_commit_hash": commit_hash,
        "payload_bytes_sha256": payload_bytes_hash,
        "signature": signature,
        "public_key": public_key,
        "verification_instructions": verification_instructions,
        "signer_id": signer_id,
        "role": role,
        "signer_type": signer_type,
    }
    return block


def sign_artifact(
    artifact_path: Path,
    algorithm: str,
    key_id: str,
    key_b64: str,
    out_path: Path | None = None,
    signer_id: str | None = None,
    role: str | None = None,
    signer_type: str | None = None,
) -> Path:
    """Sign an artifact and write the .sig.json file. Returns sig path."""
    sig_block = build_signature_block(
        artifact_path, algorithm, key_id, key_b64,
        signer_id=signer_id, role=role, signer_type=signer_type,
    )

    if out_path is None:
        out_path = artifact_path.parent / (artifact_path.name + ".sig.json")

    with open(out_path, "w") as f:
        f.write(json.dumps(sig_block, indent=2, sort_keys=True))

    return out_path


def append_signature(
    artifact_path: Path,
    algorithm: str,
    key_id: str,
    key_b64: str,
    signer_id: str | None = None,
    role: str | None = None,
    sig_path: Path | None = None,
) -> Path:
    """Append a signature to an existing .sig.json, creating a multisig envelope.

    If the existing file is a single sig block, wraps it in a multisig envelope first.
    Returns the sig path.
    """
    if sig_path is None:
        sig_path = artifact_path.parent / (artifact_path.name + ".sig.json")

    # Build the new signature entry
    new_block = build_signature_block(
        artifact_path, algorithm, key_id, key_b64,
        signer_id=signer_id, role=role,
    )

    # Convert to multisig signature entry format
    new_sig_entry = {
        "signer_id": signer_id or key_id,
        "role": role or "operator",
        "algorithm": new_block["algorithm"],
        "signing_key_id": key_id,
        "signed_at": new_block["signed_at"],
        "signature": new_block["signature"],
        "public_key": new_block.get("public_key"),
    }

    if sig_path.exists():
        existing = json.loads(sig_path.read_text())

        if "multisig_version" in existing:
            # Already a multisig envelope — just append
            existing["signatures"].append(new_sig_entry)
            ms_block = existing
        elif "sig_version" in existing:
            # Single sig — wrap in multisig envelope
            first_entry = {
                "signer_id": existing.get("signer_id") or existing.get("signing_key_id", ""),
                "role": existing.get("role") or "operator",
                "algorithm": existing["algorithm"],
                "signing_key_id": existing["signing_key_id"],
                "signed_at": existing["signed_at"],
                "signature": existing["signature"],
                "public_key": existing.get("public_key"),
            }
            ms_block = {
                "multisig_version": "1.0",
                "artifact_hash": existing.get("payload_bytes_sha256", ""),
                "threshold": 1,
                "signatures": [first_entry, new_sig_entry],
                "witness_requirements": None,
            }
        else:
            raise ValueError(f"Unknown signature format in {sig_path}")
    else:
        # No existing sig — create multisig with just this one
        ms_block = {
            "multisig_version": "1.0",
            "artifact_hash": new_block["payload_bytes_sha256"],
            "threshold": 1,
            "signatures": [new_sig_entry],
            "witness_requirements": None,
        }

    with open(sig_path, "w") as f:
        f.write(json.dumps(ms_block, indent=2, sort_keys=True))

    return sig_path


# ── Main ─────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Sign a sealed governance artifact")
    parser.add_argument("--file", type=Path, required=True, help="Artifact to sign")
    parser.add_argument("--algo", required=True, choices=["ed25519", "hmac"],
                        help="Signing algorithm")
    parser.add_argument("--key-id", required=True, help="Key ID (e.g. ds-dev-2026-02)")
    parser.add_argument("--key", default=None,
                        help="Base64 key (or set DEEPSIGMA_SIGNING_KEY env)")
    parser.add_argument("--out", type=Path, default=None, help="Output .sig.json path")
    parser.add_argument("--witness", default=None, help="Signer name/ID")
    parser.add_argument("--role", default=None,
                        choices=["operator", "reviewer", "witness", "auditor"],
                        help="Signer role")
    parser.add_argument("--append", action="store_true",
                        help="Append to existing sig (creates multisig envelope)")
    args = parser.parse_args()

    # Resolve key
    key_b64 = args.key or os.environ.get("DEEPSIGMA_SIGNING_KEY")
    if not key_b64:
        print("ERROR: Provide --key or set DEEPSIGMA_SIGNING_KEY env", file=sys.stderr)
        return 1

    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        return 1

    if args.append:
        sig_path = append_signature(
            args.file, args.algo, args.key_id, key_b64,
            signer_id=args.witness, role=args.role, sig_path=args.out,
        )
        print(f"Appended signature: {args.file}")
    else:
        sig_path = sign_artifact(
            args.file, args.algo, args.key_id, key_b64, args.out,
            signer_id=args.witness, role=args.role,
        )
        print(f"Signed: {args.file}")

    print(f"  Algorithm:  {args.algo}")
    print(f"  Key ID:     {args.key_id}")
    if args.witness:
        print(f"  Signer:     {args.witness} ({args.role or 'operator'})")
    print(f"  Signature:  {sig_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
