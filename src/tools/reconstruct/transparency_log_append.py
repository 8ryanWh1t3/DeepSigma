#!/usr/bin/env python3
"""Transparency log: append entries and verify chain integrity.

Each entry chains to the previous via prev_entry_hash, forming a
tamper-evident log. Modifying any entry invalidates all successors.

Usage:
    # Append
    python src/tools/reconstruct/transparency_log_append.py \\
        --log-path artifacts/transparency_log/log.ndjson \\
        --run-id RUN-abc12345 \\
        --commit-hash sha256:... \\
        --sealed-hash sha256:...

    # Verify chain
    python src/tools/reconstruct/transparency_log_append.py \\
        --log-path artifacts/transparency_log/log.ndjson \\
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


def _last_entry(log_path: Path) -> dict | None:
    """Read the last non-empty line of the NDJSON log."""
    if not log_path.exists():
        return None
    text = log_path.read_text().strip()
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


def append_entry(
    log_path: Path,
    run_id: str,
    commit_hash: str,
    sealed_hash: str,
    signing_key_id: str | None = None,
    artifact_path: str | None = None,
    witness_key_id: str | None = None,
) -> dict:
    """Append a new entry to the transparency log. Returns the entry dict."""
    prev = _last_entry(log_path)
    prev_hash = prev["entry_hash"] if prev else None

    # Deterministic entry ID
    id_payload = canonical_dumps({
        "run_id": run_id,
        "commit_hash": commit_hash,
        "sealed_hash": sealed_hash,
    })
    entry_id = det_id("TLE", sha256_text(id_payload))

    entry = {
        "entry_version": "1.0",
        "entry_id": entry_id,
        "run_id": run_id,
        "commit_hash": commit_hash,
        "artifact_bytes_sha256": sealed_hash,
        "artifact_path": artifact_path,
        "signing_key_id": signing_key_id,
        "witness_key_id": witness_key_id,
        "prev_entry_hash": prev_hash,
        "entry_hash": "",
        "observed_at": observed_now(),
    }

    entry["entry_hash"] = _compute_entry_hash(entry)

    # Append to log
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    return entry


def verify_chain(log_path: Path) -> list[tuple[int, bool, str]]:
    """Verify the integrity of the entire transparency log.

    Returns list of (line_number, passed, detail) tuples.
    """
    results: list[tuple[int, bool, str]] = []

    if not log_path.exists():
        results.append((0, False, "Log file not found"))
        return results

    text = log_path.read_text().strip()
    if not text:
        results.append((0, True, "Empty log (no entries)"))
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
                results.append((line_num, True, f"Chain link valid"))
            else:
                results.append((
                    line_num, False,
                    f"Chain break: prev should be {str(prev_hash)[:30]}... but is {str(recorded_prev)[:30]}...",
                ))

        prev_hash = entry.get("entry_hash")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Transparency log: append or verify")
    parser.add_argument("--log-path", type=Path, required=True, help="Path to log.ndjson")
    parser.add_argument("--verify-only", action="store_true", help="Only verify chain integrity")
    parser.add_argument("--run-id", default=None, help="Run ID")
    parser.add_argument("--commit-hash", default=None, help="Commit hash")
    parser.add_argument("--sealed-hash", default=None, help="Sealed artifact bytes hash")
    parser.add_argument("--signing-key-id", default=None, help="Signing key ID")
    parser.add_argument("--artifact-path", default=None, help="Artifact file path")
    args = parser.parse_args()

    if args.verify_only:
        results = verify_chain(args.log_path)
        print("=" * 55)
        print("  Transparency Log Verification")
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

    # Append mode
    if not args.run_id or not args.commit_hash or not args.sealed_hash:
        print("ERROR: --run-id, --commit-hash, and --sealed-hash required for append",
              file=sys.stderr)
        return 1

    entry = append_entry(
        log_path=args.log_path,
        run_id=args.run_id,
        commit_hash=args.commit_hash,
        sealed_hash=args.sealed_hash,
        signing_key_id=args.signing_key_id,
        artifact_path=args.artifact_path,
    )

    print(f"Appended: {entry['entry_id']}")
    print(f"  Run:        {entry['run_id']}")
    print(f"  Commit:     {entry['commit_hash'][:40]}...")
    print(f"  Entry hash: {entry['entry_hash'][:40]}...")
    print(f"  Prev hash:  {entry['prev_entry_hash'] or '(none — chain head)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
