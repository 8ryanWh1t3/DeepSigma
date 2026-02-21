#!/usr/bin/env python3
"""Verify a multi-signature block on a sealed governance artifact.

Checks that at least `threshold` valid signatures exist from distinct key IDs.

Usage:
    python src/tools/reconstruct/verify_multisig.py \\
        --file <sealed_run>.json \\
        --multisig <sealed_run>.json.sig.json \\
        --threshold 2 \\
        --key "$DEEPSIGMA_SIGNING_KEY"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_bytes
from verify_signature import VerifyResult, verify_hmac, verify_ed25519


def verify_multisig(
    artifact_path: Path,
    multisig_path: Path,
    threshold: int,
    keys: dict[str, str] | None = None,
    key_b64: str | None = None,
    public_key_b64: str | None = None,
) -> VerifyResult:
    """Verify a multi-signature block against an artifact.

    Args:
        artifact_path: Path to the signed artifact.
        multisig_path: Path to the multisig .sig.json file.
        threshold: Minimum valid signatures required.
        keys: Optional mapping of key_id -> key_b64 for per-signer keys.
        key_b64: Fallback shared key (HMAC) for all signers.
        public_key_b64: Fallback public key (Ed25519) for all signers.
    """
    result = VerifyResult()

    if not artifact_path.exists():
        result.check("artifact.exists", False, f"Not found: {artifact_path}")
        return result
    result.check("artifact.exists", True, str(artifact_path))

    if not multisig_path.exists():
        result.check("multisig.exists", False, f"Not found: {multisig_path}")
        return result
    result.check("multisig.exists", True, str(multisig_path))

    try:
        artifact = json.loads(artifact_path.read_bytes())
    except json.JSONDecodeError as e:
        result.check("artifact.json", False, str(e))
        return result

    try:
        ms_block = json.loads(multisig_path.read_bytes())
    except json.JSONDecodeError as e:
        result.check("multisig.json", False, str(e))
        return result

    # Check version
    result.check(
        "multisig.version",
        ms_block.get("multisig_version") == "1.0",
        f"version={ms_block.get('multisig_version')}",
    )

    # Compute canonical bytes
    canonical_bytes = canonical_dumps(artifact).encode("utf-8")

    # Verify each signature
    sigs = ms_block.get("signatures", [])
    valid_count = 0
    seen_key_ids: set[str] = set()

    for i, sig in enumerate(sigs):
        sig_key_id = sig.get("signing_key_id", "")
        algo = sig.get("algorithm", "")
        sig_b64 = sig.get("signature", "")

        # Resolve key for this signer
        signer_key = None
        signer_pub = None
        if keys and sig_key_id in keys:
            signer_key = keys[sig_key_id]
        else:
            signer_key = key_b64
            signer_pub = public_key_b64

        valid = False
        if algo == "hmac-sha256" and signer_key:
            valid = verify_hmac(canonical_bytes, sig_b64, signer_key)
        elif algo == "ed25519":
            pub = signer_pub or sig.get("public_key")
            if pub:
                valid = verify_ed25519(canonical_bytes, sig_b64, pub)

        detail = f"{sig.get('signer_id', '?')} ({sig.get('role', '?')}) key={sig_key_id}"
        result.check(f"multisig.sig[{i}]", valid, f"{'PASS' if valid else 'FAIL'}: {detail}")

        if valid:
            valid_count += 1
            seen_key_ids.add(sig_key_id)

    # Check distinct keys
    result.check(
        "multisig.distinct_keys",
        len(seen_key_ids) == valid_count,
        f"{len(seen_key_ids)} distinct keys from {valid_count} valid sigs",
    )

    # Check threshold
    result.check(
        "multisig.quorum",
        valid_count >= threshold,
        f"{valid_count}/{threshold} valid signatures",
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify multi-signature on sealed artifact")
    parser.add_argument("--file", type=Path, required=True, help="Artifact path")
    parser.add_argument("--multisig", type=Path, default=None,
                        help="Multisig file (default: <file>.sig.json)")
    parser.add_argument("--threshold", type=int, required=True, help="Required signature count")
    parser.add_argument("--key", default=None, help="Base64 shared key (HMAC)")
    parser.add_argument("--public-key", default=None, help="Base64 public key (Ed25519)")
    args = parser.parse_args()

    ms_path = args.multisig or Path(str(args.file) + ".sig.json")

    result = verify_multisig(
        artifact_path=args.file,
        multisig_path=ms_path,
        threshold=args.threshold,
        key_b64=args.key,
        public_key_b64=args.public_key,
    )

    print("=" * 55)
    print("  Multi-Signature Verification Report")
    print("=" * 55)
    for name, passed, detail in result.checks:
        icon = "PASS" if passed else "FAIL"
        detail_str = f"  ({detail})" if detail else ""
        print(f"  [{icon}] {name}{detail_str}")
    print("-" * 55)
    if result.passed:
        print("  RESULT: MULTI-SIGNATURE VALID")
    else:
        print("  RESULT: MULTI-SIGNATURE INVALID")
    print("=" * 55)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
