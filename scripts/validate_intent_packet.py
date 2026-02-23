#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = [
    "intent_statement",
    "scope",
    "success_criteria",
    "ttl_expires_at",
    "author",
    "authority",
    "intent_hash",
]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 2


def parse_ttl(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate(path: Path, now: datetime | None = None) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("intent packet must be a JSON object")

    for key in REQUIRED_FIELDS:
        if key not in data:
            raise ValueError(f"intent packet missing field: {key}")

    ttl = parse_ttl(str(data["ttl_expires_at"]))
    ref = now or datetime.now(timezone.utc)
    if ref > ttl:
        raise ValueError("intent TTL expired")


def run_self_check() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid = root / "intent_valid.json"
        valid.write_text(
            json.dumps(
                {
                    "intent_statement": "run governance check",
                    "scope": "pilot",
                    "success_criteria": "gate pass",
                    "ttl_expires_at": "2099-01-01T00:00:00Z",
                    "author": {"id": "ops"},
                    "authority": {"id": "approver"},
                    "intent_hash": "abc",
                }
            ),
            encoding="utf-8",
        )
        validate(valid)

        expired = root / "intent_expired.json"
        expired.write_text(
            json.dumps(
                {
                    "intent_statement": "expired",
                    "scope": "pilot",
                    "success_criteria": "n/a",
                    "ttl_expires_at": "2000-01-01T00:00:00Z",
                    "author": {"id": "ops"},
                    "authority": {"id": "approver"},
                    "intent_hash": "abc",
                }
            ),
            encoding="utf-8",
        )
        try:
            validate(expired)
            return fail("expired intent should fail validation")
        except ValueError:
            pass

    print("PASS: intent packet self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate intent packet with TTL enforcement")
    parser.add_argument("--path", default="runs/intent_packet.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        validate(Path(args.path))
    except Exception as exc:
        return fail(str(exc))

    print("PASS: intent packet valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
