#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def load_record(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("decision record must be an object")
    return data


def validate(record: dict[str, Any]) -> None:
    claims = record.get("claims")
    evidence = record.get("evidence")
    authority_refs = record.get("authority_refs")

    if not isinstance(claims, list) or not claims:
        raise ValueError("claims[] required")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence[] required")
    if not isinstance(authority_refs, list) or not authority_refs:
        raise ValueError("authority_refs[] required")

    evidence_ids = {e.get("id") for e in evidence if isinstance(e, dict)}
    authority_ids = {a.get("id") for a in authority_refs if isinstance(a, dict)}

    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ValueError(f"claim[{idx}] must be object")
        evid = claim.get("evidence_id")
        auth = claim.get("authority_id")
        if evid not in evidence_ids:
            raise ValueError(f"claim[{idx}] has unknown evidence_id '{evid}'")
        if auth not in authority_ids:
            raise ValueError(f"claim[{idx}] has unknown authority_id '{auth}'")


def run_self_check() -> int:
    sample = {
        "claims": [{"id": "c1", "evidence_id": "e1", "authority_id": "a1"}],
        "evidence": [{"id": "e1", "hash": "h1"}],
        "authority_refs": [{"id": "a1", "role": "dri"}],
    }
    validate(sample)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "decision_record.json"
        path.write_text(json.dumps(sample), encoding="utf-8")
        validate(load_record(path))
    print("PASS: claim/evidence/authority validator self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate claim->evidence->authority binding")
    parser.add_argument("--record", default="artifacts/decision_record.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_check:
            return run_self_check()
        record = load_record(Path(args.record))
        validate(record)
    except Exception as exc:
        return fail(str(exc))

    print("PASS: claim/evidence/authority binding is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
