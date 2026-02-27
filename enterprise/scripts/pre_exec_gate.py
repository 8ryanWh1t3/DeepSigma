#!/usr/bin/env python3

"""
Pre-execution accountability boundary (default deny).
Halts on ambiguity.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 2


def pass_msg(msg: str) -> int:
    print(f"PASS: {msg}")
    return 0


def validate_decision_record(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("claims") or not data.get("evidence") or not data.get("authority_refs"):
        raise ValueError("decision_record incomplete (claims/evidence/authority_refs required)")


def run_gate(
    intent_path: Path,
    authority_path: Path,
    snapshot_path: Path,
    decision_path: Path | None,
) -> None:
    check = subprocess.run(
        [sys.executable, "enterprise/scripts/validate_intent_packet.py", "--path", str(intent_path)],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        raise ValueError(f"intent validation failed: {(check.stdout + check.stderr).strip()}")

    if not authority_path.exists():
        raise FileNotFoundError(f"{authority_path} missing")
    if not snapshot_path.exists():
        raise FileNotFoundError(f"{snapshot_path} missing")

    auth_data = json.loads(authority_path.read_text(encoding="utf-8"))
    if auth_data.get("allow_execution") is not True:
        raise ValueError("authority_contract missing allow_execution=true (default deny)")
    if auth_data.get("allow_execution") not in (True, False):
        raise ValueError("ambiguous allow_execution value")

    signer = auth_data.get("signer")
    signer_conflict = auth_data.get("signer_conflict")
    if signer_conflict and signer_conflict != signer:
        raise ValueError("conflicting authority claims detected")

    if decision_path and decision_path.exists():
        validate_decision_record(decision_path)


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        intent = root / "intent_packet.json"
        authority = root / "authority_contract.json"
        snapshot = root / "input_snapshot.json"
        decision = root / "decision_record.json"

        intent.write_text(
            json.dumps(
                {
                    "intent_statement": "apply patch",
                    "scope": "pilot",
                    "success_criteria": "ci>=90",
                    "ttl_expires_at": "2099-01-01T00:00:00Z",
                    "author": {"id": "ops"},
                    "authority": {"id": "dri"},
                    "intent_hash": "abc",
                }
            ),
            encoding="utf-8",
        )
        authority.write_text(
            json.dumps({"allow_execution": True, "signer": "dri"}),
            encoding="utf-8",
        )
        snapshot.write_text(json.dumps({"snapshot_id": "s1"}), encoding="utf-8")
        decision.write_text(
            json.dumps(
                {"claims": [{"id": "c1"}], "evidence": [{"id": "e1"}], "authority_refs": [{"id": "a1"}]}
            ),
            encoding="utf-8",
        )

        run_gate(intent, authority, snapshot, decision)

        bad_auth = root / "authority_bad.json"
        bad_auth.write_text(json.dumps({"allow_execution": False}), encoding="utf-8")
        try:
            run_gate(intent, bad_auth, snapshot, decision)
            return fail("default deny should block when allow_execution is false")
        except ValueError:
            pass

        conflict_auth = root / "authority_conflict.json"
        conflict_auth.write_text(
            json.dumps({"allow_execution": True, "signer": "a", "signer_conflict": "b"}),
            encoding="utf-8",
        )
        try:
            run_gate(intent, conflict_auth, snapshot, decision)
            return fail("conflicting authority claims should fail")
        except ValueError:
            pass

    return pass_msg("pre-exec self-check passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-execution accountability gate")
    parser.add_argument("--intent", default="runs/intent_packet.json")
    parser.add_argument("--authority-contract", default="runs/authority_contract.json")
    parser.add_argument("--snapshot", default="runs/input_snapshot.json")
    parser.add_argument("--decision-record", default="runs/decision_record.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        decision_path = Path(args.decision_record) if args.decision_record else None
        run_gate(Path(args.intent), Path(args.authority_contract), Path(args.snapshot), decision_path)
    except Exception as exc:
        return fail(str(exc))

    return pass_msg("pre-exec gate satisfied (default deny posture enforced)")


if __name__ == "__main__":
    raise SystemExit(main())
