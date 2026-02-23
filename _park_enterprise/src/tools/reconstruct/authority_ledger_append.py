#!/usr/bin/env python3
"""Authority ledger: append entries, revoke grants, and verify chain integrity.

Each entry chains to the previous via prev_entry_hash, forming a
tamper-evident authority record. Revocations are appended as new entries
with grant_type="revocation".

Usage:
    # Append a new authority grant
    python src/tools/reconstruct/authority_ledger_append.py \\
        --ledger-path artifacts/authority_ledger/ledger.ndjson \\
        --authority-id GOV-2.1 \\
        --actor-id alice --actor-role Operator \\
        --grant-type direct \\
        --scope '{"decisions":["*"],"claims":[],"patches":[],"prompts":[],"datasets":[]}' \\
        --policy-version GOV-2.0.2 --policy-hash sha256:... \\
        --effective-at 2026-02-21T00:00:00Z

    # Revoke an authority grant
    python src/tools/reconstruct/authority_ledger_append.py \\
        --ledger-path artifacts/authority_ledger/ledger.ndjson \\
        --revoke GOV-2.1 --revocation-reason "Policy expired"

    # Verify chain
    python src/tools/reconstruct/authority_ledger_append.py \\
        --ledger-path artifacts/authority_ledger/ledger.ndjson \\
        --verify-only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_text
from deterministic_ids import det_id
from time_controls import observed_now


DEFAULT_SCOPE = {
    "decisions": [],
    "claims": [],
    "patches": [],
    "prompts": [],
    "datasets": [],
}


def _last_entry(ledger_path: Path) -> dict | None:
    """Read the last non-empty line of the NDJSON ledger."""
    if not ledger_path.exists():
        return None
    text = ledger_path.read_text().strip()
    if not text:
        return None
    last_line = text.split("\n")[-1].strip()
    if not last_line:
        return None
    return json.loads(last_line)


def _compute_entry_hash(entry: dict) -> str:
    """Compute hash of an entry with entry_hash set to empty string."""
    copy = dict(entry)
    copy["entry_hash"] = ""
    return sha256_text(canonical_dumps(copy))


def _read_all_entries(ledger_path: Path) -> list[dict]:
    """Read all entries from ledger."""
    if not ledger_path.exists():
        return []
    text = ledger_path.read_text().strip()
    if not text:
        return []
    entries = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def append_entry(
    ledger_path: Path,
    authority_id: str,
    actor_id: str,
    actor_role: str,
    grant_type: str,
    scope_bound: dict | None = None,
    policy_version: str = "",
    policy_hash: str = "",
    effective_at: str = "",
    expires_at: str | None = None,
    revoked_at: str | None = None,
    revocation_reason: str | None = None,
    witness_required: bool = False,
    witness_role: str | None = None,
    signing_key_id: str | None = None,
    notes: str = "",
) -> dict:
    """Append a new entry to the authority ledger. Returns the entry dict."""
    prev = _last_entry(ledger_path)
    prev_hash = prev["entry_hash"] if prev else None

    scope = scope_bound if scope_bound is not None else dict(DEFAULT_SCOPE)

    # Deterministic entry ID
    id_payload = canonical_dumps({
        "authority_id": authority_id,
        "actor_id": actor_id,
        "effective_at": effective_at,
    })
    entry_id = det_id("AUTH", sha256_text(id_payload))

    entry = {
        "entry_version": "1.0",
        "entry_id": entry_id,
        "authority_id": authority_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "grant_type": grant_type,
        "scope_bound": scope,
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "effective_at": effective_at,
        "expires_at": expires_at,
        "revoked_at": revoked_at,
        "revocation_reason": revocation_reason,
        "witness_required": witness_required,
        "witness_role": witness_role,
        "signing_key_id": signing_key_id,
        "signature_ref": None,
        "commit_hash_refs": [],
        "notes": notes,
        "prev_entry_hash": prev_hash,
        "entry_hash": "",
        "observed_at": observed_now(),
    }

    entry["entry_hash"] = _compute_entry_hash(entry)

    # Append to ledger
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    return entry


def revoke_entry(
    ledger_path: Path,
    authority_id: str,
    reason: str,
    clock: str | None = None,
) -> dict:
    """Revoke an authority grant by appending a revocation entry."""
    # Find the original grant to copy actor info
    original = None
    for e in _read_all_entries(ledger_path):
        if e.get("authority_id") == authority_id and e.get("grant_type") != "revocation":
            original = e

    if not original:
        raise ValueError(f"Authority grant '{authority_id}' not found in ledger")

    revoked_at = clock or observed_now()

    return append_entry(
        ledger_path=ledger_path,
        authority_id=authority_id,
        actor_id=original["actor_id"],
        actor_role=original["actor_role"],
        grant_type="revocation",
        scope_bound=original.get("scope_bound"),
        policy_version=original.get("policy_version", ""),
        policy_hash=original.get("policy_hash", ""),
        effective_at=revoked_at,
        revoked_at=revoked_at,
        revocation_reason=reason,
        notes=f"Revocation of {authority_id}",
    )


def verify_chain(ledger_path: Path) -> list[tuple[int, bool, str]]:
    """Verify the integrity of the entire authority ledger.

    Returns list of (line_number, passed, detail) tuples.
    """
    results: list[tuple[int, bool, str]] = []

    if not ledger_path.exists():
        results.append((0, False, "Ledger file not found"))
        return results

    text = ledger_path.read_text().strip()
    if not text:
        results.append((0, True, "Empty ledger (no entries)"))
        return results

    lines = text.split("\n")
    prev_hash: str | None = None

    for i, line in enumerate(lines):
        line_num = i + 1
        line = line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            results.append((line_num, False, f"Invalid JSON: {e}"))
            continue

        # Verify entry_hash
        computed = _compute_entry_hash(entry)
        recorded = entry.get("entry_hash", "")
        if computed != recorded:
            results.append((
                line_num, False,
                f"entry_hash mismatch: computed {computed[:30]}... != recorded {recorded[:30]}...",
            ))
        else:
            results.append((line_num, True, f"entry_hash valid ({entry.get('entry_id', '?')})"))

        # Verify chain link
        recorded_prev = entry.get("prev_entry_hash")
        if i == 0:
            if recorded_prev is not None and prev_hash is None:
                results.append((line_num, False, "First entry should have null prev_entry_hash"))
            else:
                results.append((line_num, True, "Chain head (prev=null)"))
        else:
            if recorded_prev == prev_hash:
                results.append((line_num, True, "Chain link valid"))
            else:
                results.append((
                    line_num, False,
                    f"Chain break: prev should be {str(prev_hash)[:30]}... but is {str(recorded_prev)[:30]}...",
                ))

        prev_hash = entry.get("entry_hash")

    return results


def find_entry(ledger_path: Path, entry_id: str) -> dict | None:
    """Find a ledger entry by entry_id."""
    for entry in _read_all_entries(ledger_path):
        if entry.get("entry_id") == entry_id:
            return entry
    return None


def find_active_for_actor(
    ledger_path: Path,
    actor_id: str,
    at_time: str,
) -> list[dict]:
    """Find active (non-revoked, non-expired) authority entries for an actor at a given time.

    Returns entries where:
    - actor_id matches
    - grant_type is not "revocation"
    - effective_at <= at_time
    - expires_at is null OR expires_at > at_time
    - not revoked (no revocation entry with same authority_id and revoked_at <= at_time)
    """
    entries = _read_all_entries(ledger_path)

    # Collect revoked authority_ids
    revoked_ids: set[str] = set()
    for e in entries:
        if e.get("grant_type") == "revocation":
            revoked_at = e.get("revoked_at", "")
            if revoked_at and revoked_at <= at_time:
                revoked_ids.add(e.get("authority_id", ""))

    active = []
    for e in entries:
        if e.get("grant_type") == "revocation":
            continue
        if e.get("actor_id") != actor_id:
            continue
        if e.get("authority_id", "") in revoked_ids:
            continue
        eff = e.get("effective_at", "")
        if eff and eff > at_time:
            continue
        exp = e.get("expires_at")
        if exp and exp <= at_time:
            continue
        active.append(e)

    return active


def main() -> int:
    parser = argparse.ArgumentParser(description="Authority ledger: append, revoke, or verify")
    parser.add_argument("--ledger-path", type=Path, required=True,
                        help="Path to authority ledger NDJSON")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify chain integrity")

    # Append args
    parser.add_argument("--authority-id", default=None, help="Authority grant ID")
    parser.add_argument("--actor-id", default=None, help="Actor ID")
    parser.add_argument("--actor-role", default=None, help="Actor role")
    parser.add_argument("--grant-type", default=None,
                        choices=["direct", "delegated", "emergency"],
                        help="How authority was obtained")
    parser.add_argument("--scope", default=None,
                        help="Scope bound as JSON string or path to JSON file")
    parser.add_argument("--policy-version", default="", help="Policy version string")
    parser.add_argument("--policy-hash", default="", help="Policy baseline hash")
    parser.add_argument("--effective-at", default=None, help="Effective time (ISO8601)")
    parser.add_argument("--expires-at", default=None, help="Expiry time (ISO8601)")
    parser.add_argument("--witness-required", action="store_true",
                        help="Require witness co-signature")
    parser.add_argument("--witness-role", default=None, help="Required witness role")
    parser.add_argument("--signing-key-id", default=None, help="Signing key ID")
    parser.add_argument("--notes", default="", help="Free-text notes")
    parser.add_argument("--clock", default=None,
                        help="Fixed clock for effective_at (ISO8601)")

    # Revoke args
    parser.add_argument("--revoke", default=None,
                        help="Authority ID to revoke")
    parser.add_argument("--revocation-reason", default="",
                        help="Reason for revocation")

    args = parser.parse_args()

    if args.verify_only:
        results = verify_chain(args.ledger_path)
        print("=" * 55)
        print("  Authority Ledger Verification")
        print("=" * 55)
        all_ok = True
        for line_num, passed, detail in results:
            icon = "PASS" if passed else "FAIL"
            print(f"  [{icon}] Line {line_num}: {detail}")
            if not passed:
                all_ok = False
        print("-" * 55)
        print(f"  RESULT: {'CHAIN VALID' if all_ok else 'CHAIN BROKEN'}")
        print("=" * 55)
        return 0 if all_ok else 1

    if args.revoke:
        try:
            entry = revoke_entry(
                ledger_path=args.ledger_path,
                authority_id=args.revoke,
                reason=args.revocation_reason,
                clock=args.clock,
            )
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Revoked: {args.revoke}")
        print(f"  Entry ID:   {entry['entry_id']}")
        print(f"  Entry hash: {entry['entry_hash'][:40]}...")
        return 0

    # Append mode
    if not args.authority_id or not args.actor_id or not args.actor_role or not args.grant_type:
        print("ERROR: --authority-id, --actor-id, --actor-role, and --grant-type required",
              file=sys.stderr)
        return 1

    effective_at = args.effective_at or args.clock or observed_now()

    # Parse scope
    scope = None
    if args.scope:
        if Path(args.scope).exists():
            scope = json.loads(Path(args.scope).read_text())
        else:
            scope = json.loads(args.scope)

    entry = append_entry(
        ledger_path=args.ledger_path,
        authority_id=args.authority_id,
        actor_id=args.actor_id,
        actor_role=args.actor_role,
        grant_type=args.grant_type,
        scope_bound=scope,
        policy_version=args.policy_version,
        policy_hash=args.policy_hash,
        effective_at=effective_at,
        expires_at=args.expires_at,
        witness_required=args.witness_required,
        witness_role=args.witness_role,
        signing_key_id=args.signing_key_id,
        notes=args.notes,
    )

    print(f"Appended: {entry['entry_id']}")
    print(f"  Authority:  {entry['authority_id']}")
    print(f"  Actor:      {entry['actor_id']} ({entry['actor_role']})")
    print(f"  Grant type: {entry['grant_type']}")
    print(f"  Effective:  {entry['effective_at']}")
    print(f"  Entry hash: {entry['entry_hash'][:40]}...")
    print(f"  Prev hash:  {entry['prev_entry_hash'] or '(none — chain head)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
