#!/usr/bin/env python3
"""Verify Authority Boundary Primitive (ABP) v1.

Standalone verifier — also callable from verify_pack.py.

Checks:
  1. abp.schema_valid      — validates against abp_v1.json schema
  2. abp.hash_integrity    — recomputes hash, matches recorded
  3. abp.id_deterministic  — recomputes ABP ID from scope+authority_ref+created_at
  4. abp.authority_ref_valid — authority_entry_id exists in ledger, not revoked
  5. abp.authority_not_expired — authority window contains ABP created_at
  6. abp.composition_valid — parent/children refs consistent
  7. abp.no_contradictions — no objective/tool in both allow and deny

Usage:
    python enterprise/src/tools/reconstruct/verify_abp.py \\
        --abp enterprise/artifacts/public_demo_pack/abp_v1.json \\
        --ledger enterprise/artifacts/public_demo_pack/authority_ledger.ndjson
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_abp import verify_abp_hash, verify_abp_id  # noqa: E402


class VerifyAbpResult:
    """Accumulates ABP verification checks."""

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


def _parse_dt(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def verify_abp(
    abp_path: Path,
    ledger_path: Path | None = None,
    schema_path: Path | None = None,
) -> VerifyAbpResult:
    """Full ABP verification. Returns structured result with checks list."""
    result = VerifyAbpResult()

    if not abp_path.exists():
        result.check("abp.file_exists", False, f"Not found: {abp_path}")
        return result

    try:
        abp = json.loads(abp_path.read_text())
    except json.JSONDecodeError as e:
        result.check("abp.json_valid", False, str(e))
        return result
    result.check("abp.json_valid", True, "Valid JSON")

    # 1. Schema validation (optional — only if jsonschema is available)
    if schema_path is None:
        schema_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "schemas" / "reconstruct" / "abp_v1.json"
        )
    if schema_path.exists():
        try:
            import jsonschema
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(abp, schema)
            result.check("abp.schema_valid", True, "Validates against abp_v1.json")
        except ImportError:
            result.check("abp.schema_valid", True, "jsonschema not installed — skipped")
        except jsonschema.ValidationError as e:
            result.check("abp.schema_valid", False, e.message)
    else:
        result.check("abp.schema_valid", True, f"Schema not found at {schema_path} — skipped")

    # 2. Hash integrity
    hash_ok = verify_abp_hash(abp)
    result.check("abp.hash_integrity", hash_ok,
                 "Content hash verified" if hash_ok else "Hash mismatch — ABP may be tampered")

    # 3. ID deterministic
    id_ok = verify_abp_id(abp)
    result.check("abp.id_deterministic", id_ok,
                 f"ABP ID verified ({abp.get('abp_id', '?')})" if id_ok
                 else "ABP ID mismatch — not derived from scope+authority_ref+created_at")

    # 4. Authority ref valid (if ledger provided)
    if ledger_path and ledger_path.exists():
        entry_id = abp.get("authority_ref", {}).get("authority_entry_id", "")
        entry_hash = abp.get("authority_ref", {}).get("authority_entry_hash", "")
        found = False
        revoked = False
        hash_match = False
        entry_data: dict | None = None

        for line in ledger_path.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("entry_id") == entry_id:
                found = True
                hash_match = entry.get("entry_hash") == entry_hash
                revoked = entry.get("revoked_at") is not None
                entry_data = entry
                break

        if not found:
            result.check("abp.authority_ref_valid", False,
                         f"Entry {entry_id} not found in ledger")
        elif not hash_match:
            result.check("abp.authority_ref_valid", False,
                         f"Entry hash mismatch for {entry_id}")
        elif revoked:
            result.check("abp.authority_ref_valid", False,
                         f"Authority {entry_id} has been revoked")
        else:
            result.check("abp.authority_ref_valid", True,
                         f"Authority {entry_id} valid and active")

        # 5. Authority not expired
        if found and entry_data:
            eff = _parse_dt(entry_data.get("effective_at", ""))
            exp_str = entry_data.get("expires_at")
            exp = _parse_dt(exp_str) if exp_str else None
            abp_created = _parse_dt(abp.get("created_at", ""))

            if eff and abp_created:
                in_window = eff <= abp_created
                if exp:
                    in_window = in_window and abp_created <= exp
                result.check("abp.authority_not_expired", in_window,
                             "ABP created_at within authority window" if in_window
                             else "ABP created_at outside authority effective/expires window")
            else:
                result.check("abp.authority_not_expired", True,
                             "Could not parse timestamps — skipped")
    else:
        detail = "No ledger provided" if not ledger_path else f"Ledger not found: {ledger_path}"
        result.check("abp.authority_ref_valid", True, f"{detail} — skipped")
        result.check("abp.authority_not_expired", True, f"{detail} — skipped")

    # 6. Composition valid
    comp = abp.get("composition", {})
    parent_id = comp.get("parent_abp_id")
    parent_hash = comp.get("parent_abp_hash")
    children = comp.get("children", [])

    if parent_id and not parent_hash:
        result.check("abp.composition_valid", False,
                     "parent_abp_id set but parent_abp_hash is missing")
    elif not parent_id and parent_hash:
        result.check("abp.composition_valid", False,
                     "parent_abp_hash set but parent_abp_id is missing")
    else:
        child_ids = [c.get("abp_id") for c in children]
        has_dup = len(child_ids) != len(set(child_ids))
        if has_dup:
            result.check("abp.composition_valid", False, "Duplicate child ABP IDs")
        else:
            detail = f"{len(children)} children"
            if parent_id:
                detail = f"parent={parent_id}, {detail}"
            result.check("abp.composition_valid", True, detail)

    # 7. No contradictions
    allowed_obj_ids = {o["id"] for o in abp.get("objectives", {}).get("allowed", [])}
    denied_obj_ids = {o["id"] for o in abp.get("objectives", {}).get("denied", [])}
    obj_overlap = allowed_obj_ids & denied_obj_ids

    allowed_tools = {t["name"] for t in abp.get("tools", {}).get("allow", [])}
    denied_tools = {t["name"] for t in abp.get("tools", {}).get("deny", [])}
    tool_overlap = allowed_tools & denied_tools

    if obj_overlap or tool_overlap:
        parts = []
        if obj_overlap:
            parts.append(f"objectives: {obj_overlap}")
        if tool_overlap:
            parts.append(f"tools: {tool_overlap}")
        result.check("abp.no_contradictions", False,
                     f"Contradictions found — {', '.join(parts)}")
    else:
        result.check("abp.no_contradictions", True, "No contradictions")

    # 8. Delegation review (optional section — structural validation)
    dr = abp.get("delegation_review")
    if dr:
        triggers = dr.get("triggers", [])
        policy = dr.get("review_policy", {})
        trigger_ids = [t.get("id", "") for t in triggers]
        dup_ids = len(trigger_ids) != len(set(trigger_ids))
        valid_severities = all(
            t.get("severity") in ("warn", "critical") for t in triggers
        )
        has_policy = bool(policy.get("approver_role")) and bool(policy.get("output"))

        if dup_ids:
            result.check("abp.delegation_review_valid", False,
                         "Duplicate trigger IDs in delegation_review")
        elif not valid_severities:
            result.check("abp.delegation_review_valid", False,
                         "Invalid severity in delegation_review triggers (must be warn|critical)")
        elif not has_policy:
            result.check("abp.delegation_review_valid", False,
                         "delegation_review.review_policy missing approver_role or output")
        else:
            result.check("abp.delegation_review_valid", True,
                         f"{len(triggers)} triggers, policy output={policy.get('output')}")
    else:
        result.check("abp.delegation_review_valid", True,
                     "Not present (optional section)")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Authority Boundary Primitive (ABP) v1"
    )
    parser.add_argument("--abp", type=Path, required=True,
                        help="Path to abp_v1.json")
    parser.add_argument("--ledger", type=Path, default=None,
                        help="Path to authority ledger NDJSON")
    parser.add_argument("--schema", type=Path, default=None,
                        help="Path to abp_v1.json schema (auto-detected if omitted)")
    args = parser.parse_args()

    result = verify_abp(args.abp, args.ledger, args.schema)

    print("=" * 60)
    print("  ABP Verification Report")
    print("=" * 60)
    for name, passed, detail in result.checks:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}: {detail}")
    print("-" * 60)
    total = len(result.checks)
    passed_count = sum(1 for _, ok, _ in result.checks if ok)
    if result.passed:
        print(f"  RESULT: ABP VALID  ({passed_count}/{total} checks passed)")
    else:
        print(f"  RESULT: ABP INVALID  ({result.failed_count} failures)")
    print("=" * 60)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
