#!/usr/bin/env python3

"""
Generates and verifies a proof bundle:
- intent_hash
- input_snapshot_hash
- authority_contract_hash
- outputs_hash
- optional signature verification transcript
"""

import argparse
import hashlib
import json
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_proof(intent: Path, snapshot: Path, authority: Path, outputs: Path) -> dict[str, object]:
    for path in [intent, snapshot, authority, outputs]:
        if not path.exists():
            raise FileNotFoundError(f"missing required file: {path}")

    proof: dict[str, object] = {
        "intent_hash": sha256_file(intent),
        "input_snapshot_hash": sha256_file(snapshot),
        "authority_contract_hash": sha256_file(authority),
        "outputs_hash": sha256_file(outputs),
        "signature_verified": False,
        "signature_method": "none",
        "notes": [],
    }
    return proof


def maybe_verify_ed25519(proof: dict[str, object], public_key_hex: Path, signature_hex: Path) -> None:
    if not (public_key_hex.exists() and signature_hex.exists()):
        return

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except Exception as exc:
        proof["notes"].append(f"signature verification unavailable: {exc}")
        return

    try:
        pubkey_bytes = bytes.fromhex(public_key_hex.read_text(encoding="utf-8").strip())
        signature_bytes = bytes.fromhex(signature_hex.read_text(encoding="utf-8").strip())
        message = str(proof["authority_contract_hash"]).encode("utf-8")
        pub = Ed25519PublicKey.from_public_bytes(pubkey_bytes)
        pub.verify(signature_bytes, message)
        proof["signature_verified"] = True
        proof["signature_method"] = "ed25519(pub.verify(sig, authority_contract_hash))"
        proof["notes"].append("signature valid")
    except Exception as exc:
        proof["signature_verified"] = False
        proof["signature_method"] = "ed25519"
        proof["notes"].append(f"signature verification failed: {exc}")


def run_self_check() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        intent = root / "intent.json"
        snap = root / "snapshot.json"
        auth = root / "authority.json"
        out = root / "outputs.json"
        for path, payload in [
            (intent, {"i": 1}),
            (snap, {"s": 1}),
            (auth, {"a": 1}),
            (out, {"o": 1}),
        ]:
            path.write_text(json.dumps(payload), encoding="utf-8")

        proof = build_proof(intent, snap, auth, out)
        required = {"intent_hash", "input_snapshot_hash", "authority_contract_hash", "outputs_hash"}
        if not required.issubset(proof.keys()):
            return fail("proof bundle missing required fields")

        try:
            build_proof(intent, snap, auth, root / "missing.json")
            return fail("missing outputs should fail proof generation")
        except FileNotFoundError:
            pass

    print("PASS: crypto proof self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate cryptographic proof bundle")
    parser.add_argument("--intent", default="runs/intent_packet.json")
    parser.add_argument("--snapshot", default="runs/input_snapshot.json")
    parser.add_argument("--authority", default="runs/authority_contract.json")
    parser.add_argument("--outputs", default="runs/outputs_manifest.json")
    parser.add_argument("--public-key", default="runs/public_key.hex")
    parser.add_argument("--signature", default="runs/authority_signature.hex")
    parser.add_argument("--out", default="runs/proof_bundle.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        proof = build_proof(Path(args.intent), Path(args.snapshot), Path(args.authority), Path(args.outputs))
        maybe_verify_ed25519(proof, Path(args.public_key), Path(args.signature))
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    except Exception as exc:
        return fail(str(exc))

    print(f"PASS: proof bundle generated -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
