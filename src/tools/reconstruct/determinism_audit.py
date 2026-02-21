#!/usr/bin/env python3
"""Determinism Audit — verify a sealed run meets determinism requirements.

Checks:
  1. hash_scope present
  2. clock fixed (non-null)
  3. deterministic flag set
  4. observed_at excluded
  5. run_id is deterministic (matches det_id)
  6. no UUID v4 patterns
  7. committed_at matches clock parameter
  8. inputs_commitments present (v1.3+)
  9. canonical JSON re-serialization matches

Exit codes:
  0  CLEAN (all checks pass)
  1  WARNINGS (non-critical issues)
  2  VIOLATIONS (strict mode failures)

Usage:
    python src/tools/reconstruct/determinism_audit.py --sealed <path>
    python src/tools/reconstruct/determinism_audit.py --sealed <path> --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from canonical_json import canonical_dumps, sha256_text
from deterministic_ids import det_id


UUID4_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class AuditResult:
    def __init__(self) -> None:
        self.checks: list[tuple[str, str, str]] = []  # (name, level, detail)

    def ok(self, name: str, detail: str = "") -> None:
        self.checks.append((name, "ok", detail))

    def warn(self, name: str, detail: str = "") -> None:
        self.checks.append((name, "warn", detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.checks.append((name, "fail", detail))

    @property
    def warnings(self) -> int:
        return sum(1 for _, level, _ in self.checks if level == "warn")

    @property
    def violations(self) -> int:
        return sum(1 for _, level, _ in self.checks if level == "fail")

    @property
    def exit_code(self) -> int:
        if self.violations > 0:
            return 2
        if self.warnings > 0:
            return 1
        return 0


def audit_sealed_run(sealed_path: Path, strict: bool = False) -> AuditResult:
    """Run determinism audit on a sealed run."""
    result = AuditResult()

    # Load
    raw_text = sealed_path.read_text()
    sealed = json.loads(raw_text)

    # 1. hash_scope present
    hash_scope = sealed.get("hash_scope")
    if hash_scope is not None:
        result.ok("hash_scope.present", "hash_scope found")
    else:
        result.fail("hash_scope.present", "No hash_scope — pre-v1.1 sealed run")
        return result  # Can't check further without hash_scope

    # 2. clock fixed
    params = hash_scope.get("parameters", {})
    clock = params.get("clock")
    if clock is not None:
        result.ok("hash_scope.clock_fixed", f"clock={clock}")
    else:
        level = "fail" if strict else "warn"
        getattr(result, level)("hash_scope.clock_fixed", "clock is null (non-deterministic)")

    # 3. deterministic flag
    det_flag = params.get("deterministic")
    if det_flag is True:
        result.ok("hash_scope.deterministic_flag", "deterministic=true")
    else:
        level = "fail" if strict else "warn"
        getattr(result, level)("hash_scope.deterministic_flag", f"deterministic={det_flag}")

    # 4. exclusions: observed_at
    exclusions = hash_scope.get("exclusions", [])
    if "observed_at" in exclusions:
        result.ok("exclusions.observed_at", "observed_at correctly excluded")
    else:
        result.fail("exclusions.observed_at", "observed_at not in exclusion list")

    # 5. run_id deterministic
    commit_hash = sealed.get("commit_hash", "")
    provenance = sealed.get("authority_envelope", {}).get("provenance", {})
    run_id = provenance.get("run_id", "")
    if commit_hash and run_id:
        expected_run_id = det_id("RUN", commit_hash, length=8)
        if run_id == expected_run_id:
            result.ok("ids.run_id_deterministic", f"run_id={run_id} matches det_id")
        else:
            result.fail("ids.run_id_deterministic",
                        f"run_id={run_id} != expected {expected_run_id}")
    else:
        result.warn("ids.run_id_deterministic", "Missing commit_hash or run_id")

    # 6. no UUID v4
    uuid_matches = UUID4_PATTERN.findall(raw_text)
    if not uuid_matches:
        result.ok("ids.no_uuid", "No UUID v4 patterns found")
    else:
        result.fail("ids.no_uuid", f"Found {len(uuid_matches)} UUID v4 pattern(s)")

    # 7. committed_at matches clock
    if clock:
        committed_at = sealed.get("authority_envelope", {}).get("authority", {}).get("effective_at", "")
        if committed_at == clock:
            result.ok("timestamps.committed_at_matches_clock",
                       f"committed_at={committed_at}")
        else:
            result.warn("timestamps.committed_at_matches_clock",
                        f"committed_at={committed_at} != clock={clock}")

    # 8. commitments present (v1.3+)
    commitments = sealed.get("inputs_commitments")
    if commitments is not None:
        result.ok("commitments.present", "inputs_commitments found")
    else:
        level = "fail" if strict else "warn"
        getattr(result, level)("commitments.present", "No inputs_commitments (pre-v1.3)")

    # 9. canonical JSON valid — re-serialize and compare hash
    copy = dict(sealed)
    copy["hash"] = ""
    recomputed = sha256_text(canonical_dumps(copy))
    recorded_hash = sealed.get("hash", "")
    if recomputed == recorded_hash:
        result.ok("canonical.json_valid", "Re-serialization hash matches")
    else:
        result.fail("canonical.json_valid",
                    f"Hash mismatch: {recomputed[:30]}... != {recorded_hash[:30]}...")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Determinism Audit for sealed runs")
    parser.add_argument("--sealed", type=Path, required=True, help="Sealed run JSON path")
    parser.add_argument("--strict", action="store_true",
                        help="Strict mode: warnings become violations")
    args = parser.parse_args()

    if not args.sealed.exists():
        print(f"ERROR: Not found: {args.sealed}", file=sys.stderr)
        return 2

    result = audit_sealed_run(args.sealed, strict=args.strict)

    # Print report
    print("=" * 55)
    print("  Determinism Audit Report")
    print("=" * 55)

    for name, level, detail in result.checks:
        icon = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}[level]
        detail_str = f"  ({detail})" if detail else ""
        print(f"  [{icon}] {name}{detail_str}")

    print("-" * 55)
    total = len(result.checks)
    ok_count = sum(1 for _, lvl, _ in result.checks if lvl == "ok")
    print(f"  {ok_count}/{total} checks passed", end="")
    if result.warnings:
        print(f", {result.warnings} warnings", end="")
    if result.violations:
        print(f", {result.violations} violations", end="")
    print()

    if result.violations:
        print("  RESULT: VIOLATIONS FOUND")
    elif result.warnings:
        print("  RESULT: WARNINGS (clean in non-strict mode)")
    else:
        print("  RESULT: CLEAN")
    print("=" * 55)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
