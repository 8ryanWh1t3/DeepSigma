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

    return {
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
    }


def sign_artifact(
    artifact_path: Path,
    algorithm: str,
    key_id: str,
    key_b64: str,
    out_path: Path | None = None,
) -> Path:
    """Sign an artifact and write the .sig.json file. Returns sig path."""
    sig_block = build_signature_block(artifact_path, algorithm, key_id, key_b64)

    if out_path is None:
        out_path = artifact_path.parent / (artifact_path.name + ".sig.json")

    with open(out_path, "w") as f:
        f.write(json.dumps(sig_block, indent=2, sort_keys=True))

    return out_path


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
    args = parser.parse_args()

    # Resolve key
    key_b64 = args.key or os.environ.get("DEEPSIGMA_SIGNING_KEY")
    if not key_b64:
        print("ERROR: Provide --key or set DEEPSIGMA_SIGNING_KEY env", file=sys.stderr)
        return 1

    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        return 1

    sig_path = sign_artifact(args.file, args.algo, args.key_id, key_b64, args.out)

    print(f"Signed: {args.file}")
    print(f"  Algorithm:  {args.algo}")
    print(f"  Key ID:     {args.key_id}")
    print(f"  Signature:  {sig_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
