#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

HEX64 = re.compile(r"^[a-f0-9]{64}$")
REQUIRED = ["intent_hash", "authority_hash", "snapshot_hash", "outputs_hash", "chain_hash"]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected_chain_hash(payload: dict[str, str]) -> str:
    material = (
        payload["intent_hash"]
        + payload["authority_hash"]
        + payload["snapshot_hash"]
        + payload["outputs_hash"]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate(payload: dict[str, str]) -> None:
    missing = [k for k in REQUIRED if k not in payload]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    for key in REQUIRED:
        value = payload[key]
        if not isinstance(value, str) or not HEX64.match(value):
            raise ValueError(f"{key} must be a 64-char lowercase hex sha256")

    computed = expected_chain_hash(payload)
    if payload["chain_hash"] != computed:
        raise ValueError("chain_hash mismatch from bound hash chain inputs")


def run_self_check() -> int:
    seed = {
        "intent_hash": sha256_text("intent"),
        "authority_hash": sha256_text("authority"),
        "snapshot_hash": sha256_text("snapshot"),
        "outputs_hash": sha256_text("outputs"),
    }
    sample = dict(seed)
    sample["chain_hash"] = expected_chain_hash(sample)
    validate(sample)

    bad = dict(sample)
    bad["chain_hash"] = "0" * 64
    try:
        validate(bad)
        return fail("invalid chain_hash should fail validation")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "decision_episode_chain.json"
        path.write_text(json.dumps(sample), encoding="utf-8")
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate(payload)

    print("PASS: decision episode chain self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate decision episode chain binding")
    parser.add_argument("--input", default="artifacts/decision_episode_chain.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return fail("input must be a JSON object")
        validate(payload)
    except Exception as exc:
        return fail(str(exc))

    print("PASS: decision episode chain binding is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
