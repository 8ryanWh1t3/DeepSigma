#!/usr/bin/env python3

"""
Replay runner:
- validates proof bundle exists
- validates required hash-chain fields
"""

import argparse
import json
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 2


def validate_proof_bundle(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; generate proof bundle first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("proof bundle must be a JSON object")
    required = ["intent_hash", "input_snapshot_hash", "authority_contract_hash", "outputs_hash"]
    for key in required:
        if key not in data:
            raise ValueError(f"proof bundle missing {key}")


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "proof_good.json"
        bad = root / "proof_bad.json"
        good.write_text(
            json.dumps(
                {
                    "intent_hash": "a" * 64,
                    "input_snapshot_hash": "b" * 64,
                    "authority_contract_hash": "c" * 64,
                    "outputs_hash": "d" * 64,
                }
            ),
            encoding="utf-8",
        )
        validate_proof_bundle(good)

        bad.write_text(json.dumps({"intent_hash": "a" * 64}), encoding="utf-8")
        try:
            validate_proof_bundle(bad)
            return fail("incomplete proof bundle should fail validation")
        except ValueError:
            pass

    print("PASS: replay self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay run proof validation")
    parser.add_argument("--proof", default="runs/proof_bundle.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        validate_proof_bundle(Path(args.proof))
    except Exception as exc:
        return fail(str(exc))

    print("PASS: replay validation passed (proof chain present).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
