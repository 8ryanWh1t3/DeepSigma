#!/usr/bin/env python3
"""Verify a signature on a sealed governance artifact.

Recomputes hashes from the artifact, then verifies the cryptographic
signature matches.

Usage:
    # HMAC
    python src/tools/reconstruct/verify_signature.py \\
        --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \\
        --sig artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json.sig.json \\
        --key "$DEEPSIGMA_SIGNING_KEY"

    # Ed25519
    python src/tools/reconstruct/verify_signature.py \\
        --file artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json \\
        --sig artifacts/sealed_runs/RUN-abc12345_20260221T000000Z.json.sig.json \\
        --public-key <base64-public-key>
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_bytes


# ── Verification implementations ─────────────────────────────────
def verify_hmac(payload_bytes: bytes, signature_b64: str, key_b64: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    key = base64.b64decode(key_b64)
    expected = hmac.new(key, payload_bytes, hashlib.sha256).digest()
    actual = base64.b64decode(signature_b64)
    return hmac.compare_digest(expected, actual)


def verify_ed25519(payload_bytes: bytes, signature_b64: str, public_key_b64: str) -> bool:
    """Verify Ed25519 signature. Returns True on success."""
    sig_bytes = base64.b64decode(signature_b64)
    pub_bytes = base64.b64decode(public_key_b64)

    try:
        from nacl.signing import VerifyKey
        vk = VerifyKey(pub_bytes)
        vk.verify(payload_bytes, sig_bytes)
        return True
    except ImportError:
        pass
    except Exception:
        return False

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pk = Ed25519PublicKey.from_public_bytes(pub_bytes)
        pk.verify(sig_bytes, payload_bytes)
        return True
    except ImportError:
        print("ERROR: Ed25519 verification requires pynacl or cryptography.", file=sys.stderr)
        sys.exit(1)
    except Exception:
        return False

    return False


class VerifyResult:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def verify(
    artifact_path: Path,
    sig_path: Path,
    key_b64: str | None = None,
    public_key_b64: str | None = None,
) -> VerifyResult:
    """Verify a signature block against an artifact."""
    result = VerifyResult()

    # Load artifact
    if not artifact_path.exists():
        result.check("artifact.exists", False, f"Not found: {artifact_path}")
        return result
    result.check("artifact.exists", True, str(artifact_path))

    # Load signature block
    if not sig_path.exists():
        result.check("sig.exists", False, f"Not found: {sig_path}")
        return result
    result.check("sig.exists", True, str(sig_path))

    try:
        artifact = json.loads(artifact_path.read_bytes())
    except json.JSONDecodeError as e:
        result.check("artifact.json", False, str(e))
        return result
    result.check("artifact.json", True, "Valid JSON")

    try:
        sig_block = json.loads(sig_path.read_bytes())
    except json.JSONDecodeError as e:
        result.check("sig.json", False, str(e))
        return result
    result.check("sig.json", True, "Valid JSON")

    # Check sig_version
    result.check(
        "sig.version",
        sig_block.get("sig_version") == "1.0",
        f"version={sig_block.get('sig_version')}",
    )

    # Recompute payload bytes hash
    canonical_bytes = canonical_dumps(artifact).encode("utf-8")
    computed_hash = sha256_bytes(canonical_bytes)
    recorded_hash = sig_block.get("payload_bytes_sha256", "")

    if computed_hash == recorded_hash:
        result.check("payload_bytes.hash", True, f"Matched: {computed_hash[:30]}...")
    else:
        result.check("payload_bytes.hash", False,
                      f"Computed {computed_hash[:30]}... != recorded {recorded_hash[:30]}...")

    # Verify commit_hash matches
    artifact_commit = artifact.get("commit_hash", "")
    sig_commit = sig_block.get("payload_commit_hash", "")
    if artifact_commit and sig_commit:
        result.check(
            "commit_hash.match",
            artifact_commit == sig_commit,
            f"artifact={artifact_commit[:20]}... sig={sig_commit[:20]}...",
        )
    elif sig_commit:
        result.check("commit_hash.match", True, "Commit hash recorded in signature")

    # Verify cryptographic signature
    algorithm = sig_block.get("algorithm", "")
    signature_b64 = sig_block.get("signature", "")

    if algorithm == "hmac-sha256":
        if not key_b64:
            result.check("signature.verify", False, "HMAC requires --key")
            return result
        valid = verify_hmac(canonical_bytes, signature_b64, key_b64)
        result.check("signature.verify", valid,
                      "HMAC-SHA256 PASS" if valid else "HMAC-SHA256 FAIL: signature mismatch")

    elif algorithm == "ed25519":
        # Try public_key from args, then from sig block
        pub_key = public_key_b64 or sig_block.get("public_key")
        if not pub_key:
            result.check("signature.verify", False, "Ed25519 requires --public-key or embedded key")
            return result
        valid = verify_ed25519(canonical_bytes, signature_b64, pub_key)
        result.check("signature.verify", valid,
                      "Ed25519 PASS" if valid else "Ed25519 FAIL: signature mismatch")
    else:
        result.check("signature.verify", False, f"Unknown algorithm: {algorithm}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a signature on a sealed artifact")
    parser.add_argument("--file", type=Path, required=True, help="Signed artifact path")
    parser.add_argument("--sig", type=Path, default=None,
                        help="Signature file (default: <file>.sig.json)")
    parser.add_argument("--key", default=None, help="Base64 shared key (HMAC)")
    parser.add_argument("--public-key", default=None, help="Base64 public key (Ed25519)")
    args = parser.parse_args()

    sig_path = args.sig or Path(str(args.file) + ".sig.json")

    result = verify(
        artifact_path=args.file,
        sig_path=sig_path,
        key_b64=args.key,
        public_key_b64=args.public_key,
    )

    # Print report
    print("=" * 55)
    print("  Signature Verification Report")
    print("=" * 55)
    for name, passed, detail in result.checks:
        icon = "PASS" if passed else "FAIL"
        detail_str = f"  ({detail})" if detail else ""
        print(f"  [{icon}] {name}{detail_str}")
    print("-" * 55)
    if result.passed:
        print("  RESULT: SIGNATURE VALID")
    else:
        print("  RESULT: SIGNATURE INVALID")
    print("=" * 55)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
