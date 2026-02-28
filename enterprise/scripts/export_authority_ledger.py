#!/usr/bin/env python3
"""Export authority ledger to shareable JSON or NDJSON artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepsigma.security.authority_ledger import (  # noqa: E402
    export_authority_ledger,
    load_authority_ledger,
    verify_chain,
    detect_replay,
)


def _run_audit_summary(ledger_path: Path) -> int:
    """Print audit summary: chain integrity + replay detection."""
    entries = load_authority_ledger(ledger_path)
    print(f"Ledger: {ledger_path}")
    print(f"Entries: {len(entries)}")

    chain_errors = verify_chain(entries)
    replay_dups = detect_replay(entries)

    if chain_errors:
        print(f"Chain integrity: FAIL ({len(chain_errors)} errors)")
        for err in chain_errors:
            print(f"  [{err['index']}] {err['entry_id']}: {err['error']}")
    else:
        print("Chain integrity: PASS")

    if replay_dups:
        print(f"Replay detection: FAIL ({len(replay_dups)} duplicates)")
        for dup in replay_dups:
            print(f"  [{dup['index']}] {dup['entry_id']}: event_id={dup['event_id']} first at [{dup['first_seen_index']}]")
    else:
        print("Replay detection: PASS")

    return 2 if (chain_errors or replay_dups) else 0


def _run_self_check() -> int:
    """Validate export, verify_chain, and detect_replay with synthetic fixtures."""
    import json
    import tempfile

    from deepsigma.security.authority_ledger import append_authority_action_entry

    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "ledger.json"
        event = {
            "event_id": "evt-sc-1",
            "event_hash": "f" * 64,
            "tenant_id": "tenant-test",
            "occurred_at": "2026-02-27T00:00:00Z",
            "payload": {"key_id": "test-key", "key_version": 1},
        }
        append_authority_action_entry(
            ledger_path=ledger_path,
            authority_event=event,
            authority_dri="test.dri",
            authority_role="dri_approver",
            authority_reason="self-check",
            signing_key="self-check-key",
            action_type="AUTHORIZED_KEY_ROTATION",
            action_contract={"action_id": "act-sc", "dri": "test.dri", "approver": "test.dri"},
        )

        # Verify chain passes
        entries = load_authority_ledger(ledger_path)
        errors = verify_chain(entries)
        if errors:
            print(f"FAIL: verify_chain should pass on valid ledger: {errors}")
            return 2

        # Verify replay detection with no replays
        dups = detect_replay(entries)
        if dups:
            print(f"FAIL: detect_replay should find no duplicates: {dups}")
            return 2

        # Tamper test: corrupt entry_hash and verify detection
        entries[0]["entry_hash"] = "tampered"
        errors = verify_chain(entries)
        if not errors:
            print("FAIL: verify_chain should detect tampered entry_hash")
            return 2

        # Replay test: duplicate event_id
        entries_dup = load_authority_ledger(ledger_path)
        entries_dup.append(dict(entries_dup[0]))  # duplicate
        dups = detect_replay(entries_dup)
        if not dups:
            print("FAIL: detect_replay should detect duplicate event_id")
            return 2

        # Export test
        out_path = Path(tmp) / "export.json"
        export_authority_ledger(ledger_path=ledger_path, out_path=out_path, export_format="json")
        exported = json.loads(out_path.read_text(encoding="utf-8"))
        if exported["entry_count"] != 1:
            print(f"FAIL: export should have 1 entry, got {exported['entry_count']}")
            return 2

    print("PASS: authority ledger export self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export authority ledger artifact")
    parser.add_argument(
        "--ledger-path",
        default="data/security/authority_ledger.json",
        help="Path to authority ledger JSON",
    )
    parser.add_argument(
        "--out",
        default="artifacts/security/authority_ledger_export.json",
        help="Destination path",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "ndjson"],
        help="Export format",
    )
    parser.add_argument(
        "--audit-summary",
        action="store_true",
        help="Print audit summary (chain integrity + replay detection)",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run internal self-check",
    )
    args = parser.parse_args()

    if args.self_check:
        return _run_self_check()

    ledger_path = (ROOT / args.ledger_path).resolve()

    if args.audit_summary:
        return _run_audit_summary(ledger_path)

    out_path = (ROOT / args.out).resolve()
    destination = export_authority_ledger(
        ledger_path=ledger_path,
        out_path=out_path,
        export_format=args.format,
    )
    print(f"Exported {len(load_authority_ledger(ledger_path))} entries to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
