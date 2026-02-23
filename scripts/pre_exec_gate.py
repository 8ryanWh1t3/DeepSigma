#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any


REQUIRED_INTENT = [
    "intent_statement",
    "scope",
    "success_criteria",
    "ttl_expires_at",
    "author",
    "authority",
    "intent_hash",
]
REQUIRED_AUTH = ["action_type", "requested_by", "dri", "intent_hash", "signature"]
REQUIRED_SNAPSHOT = ["input_hash", "env_fingerprint"]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def parse_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected in {path}")
    return data


def require_keys(name: str, payload: dict[str, Any], keys: list[str]) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValueError(f"{name} missing keys: {', '.join(missing)}")


def validate(intent_path: Path, authority_path: Path, policy_path: Path, snapshot_path: Path) -> None:
    intent = parse_json(intent_path)
    authority = parse_json(authority_path)
    policy = parse_json(policy_path)
    snapshot = parse_json(snapshot_path)

    require_keys("intent packet", intent, REQUIRED_INTENT)
    require_keys("authority contract", authority, REQUIRED_AUTH)
    require_keys("snapshot", snapshot, REQUIRED_SNAPSHOT)

    if not isinstance(policy.get("allowed_actions", []), list):
        raise ValueError("policy.allowed_actions must be a list")

    action = authority["action_type"]
    allowed_actions = policy.get("allowed_actions", [])
    if action not in allowed_actions:
        raise ValueError(f"action '{action}' is not allowed by policy")

    if authority["intent_hash"] != intent["intent_hash"]:
        raise ValueError("authority intent_hash does not match intent packet")


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        intent = root / "intent.json"
        auth = root / "authority.json"
        policy = root / "policy.json"
        snapshot = root / "snapshot.json"

        intent.write_text(
            json.dumps(
                {
                    "intent_statement": "Patch drift record",
                    "scope": "pilot",
                    "success_criteria": "ci >= 90",
                    "ttl_expires_at": "2026-12-31T00:00:00Z",
                    "author": {"id": "ops"},
                    "authority": {"id": "approver"},
                    "intent_hash": "abc123",
                }
            ),
            encoding="utf-8",
        )
        auth.write_text(
            json.dumps(
                {
                    "action_type": "patch",
                    "requested_by": "ops",
                    "dri": "approver",
                    "intent_hash": "abc123",
                    "signature": "sig",
                }
            ),
            encoding="utf-8",
        )
        policy.write_text(json.dumps({"allowed_actions": ["patch", "seal"]}), encoding="utf-8")
        snapshot.write_text(
            json.dumps({"input_hash": "h1", "env_fingerprint": "python-3.12"}), encoding="utf-8"
        )

        validate(intent, auth, policy, snapshot)

        bad_auth = root / "authority_bad.json"
        bad_auth.write_text(
            json.dumps(
                {
                    "action_type": "patch",
                    "requested_by": "ops",
                    "dri": "approver",
                    "intent_hash": "mismatch",
                    "signature": "sig",
                }
            ),
            encoding="utf-8",
        )
        try:
            validate(intent, bad_auth, policy, snapshot)
            return fail("mismatched intent_hash should fail pre-exec gate")
        except ValueError:
            pass

        bad_policy = root / "policy_bad.json"
        bad_policy.write_text(json.dumps({"allowed_actions": ["seal"]}), encoding="utf-8")
        try:
            validate(intent, auth, bad_policy, snapshot)
            return fail("disallowed action should fail pre-exec gate")
        except ValueError:
            pass

    print("PASS: pre-exec self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-execution gate")
    parser.add_argument("--intent", default="artifacts/intent_packet.json")
    parser.add_argument("--authority-contract", default="artifacts/action_contract.json")
    parser.add_argument("--policy", default="governance/security_crypto_policy.json")
    parser.add_argument("--snapshot", default="artifacts/run_snapshot.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        try:
            return run_self_check()
        except Exception as exc:
            return fail(str(exc))

    try:
        validate(Path(args.intent), Path(args.authority_contract), Path(args.policy), Path(args.snapshot))
    except Exception as exc:
        return fail(str(exc))

    print("PASS: pre-execution gate checks satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
