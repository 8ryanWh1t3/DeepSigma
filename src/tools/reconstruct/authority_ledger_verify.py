#!/usr/bin/env python3
"""Authority ledger verifier — chain integrity + schema + signature checks.

Usage:
    python src/tools/reconstruct/authority_ledger_verify.py \\
        --ledger-path artifacts/authority_ledger/ledger.ndjson

    python src/tools/reconstruct/authority_ledger_verify.py \\
        --ledger-path artifacts/authority_ledger/ledger.ndjson \\
        --verify-sigs --key "$KEY"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_text


class VerifyLedgerResult:
    """Accumulates ledger verification checks."""

    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    @property
    def failed_count(self) -> int:
        return sum(1 for _, ok, _ in self.checks if not ok)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


def _compute_entry_hash(entry: dict) -> str:
    copy = dict(entry)
    copy["entry_hash"] = ""
    return sha256_text(canonical_dumps(copy))


def verify_ledger(
    ledger_path: Path,
    verify_sigs: bool = False,
    key_b64: str | None = None,
) -> VerifyLedgerResult:
    """Verify authority ledger integrity.

    Checks:
    - File exists and is valid NDJSON
    - Each entry_hash is correctly computed
    - prev_entry_hash chain is continuous
    - Required fields present in each entry
    - Signatures valid (if verify_sigs and signature_ref present)
    """
    result = VerifyLedgerResult()

    if not ledger_path.exists():
        result.check("file.exists", False, f"Not found: {ledger_path}")
        return result
    result.check("file.exists", True, str(ledger_path))

    text = ledger_path.read_text().strip()
    if not text:
        result.check("ledger.entries", True, "Empty ledger (no entries)")
        return result

    lines = text.split("\n")
    prev_hash: str | None = None
    entry_count = 0

    required_keys = [
        "entry_version", "entry_id", "authority_id", "actor_id",
        "actor_role", "grant_type", "scope_bound", "effective_at",
        "prev_entry_hash", "entry_hash", "observed_at",
    ]

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        entry_count += 1
        line_num = i + 1

        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            result.check(f"line_{line_num}.json", False, str(e))
            continue
        result.check(f"line_{line_num}.json", True, "Valid JSON")

        # Required keys
        missing = [k for k in required_keys if k not in entry]
        if missing:
            result.check(f"line_{line_num}.keys", False, f"Missing: {missing}")
        else:
            result.check(f"line_{line_num}.keys", True,
                         f"All required keys present ({entry.get('entry_id', '?')})")

        # entry_hash integrity
        computed = _compute_entry_hash(entry)
        recorded = entry.get("entry_hash", "")
        if computed == recorded:
            result.check(f"line_{line_num}.hash", True,
                         f"entry_hash valid ({entry.get('entry_id', '?')})")
        else:
            result.check(f"line_{line_num}.hash", False,
                         f"entry_hash mismatch: {computed[:30]}... != {recorded[:30]}...")

        # Chain link
        recorded_prev = entry.get("prev_entry_hash")
        if i == 0:
            if recorded_prev is not None and prev_hash is None:
                result.check(f"line_{line_num}.chain", False,
                             "First entry should have null prev_entry_hash")
            else:
                result.check(f"line_{line_num}.chain", True, "Chain head (prev=null)")
        else:
            if recorded_prev == prev_hash:
                result.check(f"line_{line_num}.chain", True, "Chain link valid")
            else:
                result.check(f"line_{line_num}.chain", False,
                             f"Chain break at line {line_num}")

        # Signature verification (optional)
        if verify_sigs and entry.get("signature_ref"):
            sig_path = Path(entry["signature_ref"])
            if sig_path.exists() and key_b64:
                try:
                    from verify_signature import verify_hmac
                    sig_data = json.loads(sig_path.read_text())
                    sig_ok = verify_hmac(
                        sig_data.get("signature", ""),
                        sig_data.get("payload_bytes_sha256", ""),
                        key_b64,
                    )
                    result.check(f"line_{line_num}.sig", sig_ok,
                                 "Signature verified" if sig_ok else "Signature invalid")
                except Exception as e:
                    result.check(f"line_{line_num}.sig", False, f"Sig check error: {e}")

        prev_hash = entry.get("entry_hash")

    result.check("ledger.count", True, f"{entry_count} entries verified")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authority ledger verifier — chain + schema + signature checks"
    )
    parser.add_argument("--ledger-path", type=Path, required=True,
                        help="Path to authority ledger NDJSON")
    parser.add_argument("--verify-sigs", action="store_true",
                        help="Also verify signatures on entries with signature_ref")
    parser.add_argument("--key", default=None,
                        help="Base64 HMAC key for signature verification")
    args = parser.parse_args()

    result = verify_ledger(
        args.ledger_path,
        verify_sigs=args.verify_sigs,
        key_b64=args.key,
    )

    print("=" * 60)
    print("  Authority Ledger Verification Report")
    print("=" * 60)
    for name, passed, detail in result.checks:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}: {detail}")
    print("-" * 60)
    total = len(result.checks)
    passed = sum(1 for _, ok, _ in result.checks if ok)
    if result.passed:
        print(f"  RESULT: LEDGER VALID  ({passed}/{total} checks passed)")
    else:
        print(f"  RESULT: LEDGER INVALID  ({result.failed_count} failures)")
    print("=" * 60)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
