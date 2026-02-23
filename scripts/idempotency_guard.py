#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def register_key(ledger_path: Path, key: str) -> bool:
    if ledger_path.exists():
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    else:
        payload = {"keys": []}

    keys = payload.get("keys", [])
    if not isinstance(keys, list):
        raise ValueError("ledger keys must be a list")

    if key in keys:
        return False

    keys.append(key)
    payload["keys"] = keys
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "idempotency_ledger.json"
        if not register_key(ledger, "abc"):
            return fail("first key registration should pass")
        if register_key(ledger, "abc"):
            return fail("duplicate key registration should fail")
    print("PASS: idempotency guard self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotency/replay guard")
    parser.add_argument("--ledger", default="artifacts/idempotency_ledger.json")
    parser.add_argument("--key", default=None)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if not args.key:
        return fail("--key is required outside self-check")

    try:
        inserted = register_key(Path(args.ledger), args.key)
    except Exception as exc:
        return fail(str(exc))

    if not inserted:
        return fail(f"idempotency key already used: {args.key}")

    print("PASS: idempotency key accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
