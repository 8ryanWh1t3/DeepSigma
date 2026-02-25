#!/usr/bin/env python3
"""ABP Gate — host-level enforcement for EDGE exports.

Verifies that every EDGE HTML export carries a valid embedded ABP
(Authority Boundary Primitive). Run before distribution/deployment.

Usage:
    python edge/gate_abp.py --file edge/EDGE_Hiring_UI_v1.0.0.html
    python edge/gate_abp.py --dir edge/
    python edge/gate_abp.py --dir edge/ --strict --abp-ref edge/abp_v1.json
    python edge/gate_abp.py --dir edge/ --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Import ABP verification functions from reconstruct
_RECONSTRUCT = Path(__file__).resolve().parent.parent / "enterprise" / "src" / "tools" / "reconstruct"
sys.path.insert(0, str(_RECONSTRUCT))

from build_abp import _compute_abp_hash, _compute_abp_id  # noqa: E402

# Map EDGE filenames to their expected ABP module
FILE_MODULE_MAP: dict[str, str] = {
    "EDGE_Hiring_UI": "hiring",
    "EDGE_BidNoBid_UI": "bid",
    "EDGE_ComplianceMatrix_UI": "compliance",
    "EDGE_BOE_Pricing_UI": "boe",
    "EDGE_AwardStaffing_Estimator": "award_staffing",
    "EDGE_Coherence_Dashboard": "coherence",
    "EDGE_Suite_ReadOnly": "suite_readonly",
    "EDGE_Unified": "unified",
}

# Regex to extract embedded ABP JSON from HTML
_ABP_PATTERN = re.compile(
    r'<script\s+type=["\']application/json["\']\s+id=["\']ds-abp-v1["\']>\s*(.*?)\s*</script>',
    re.DOTALL,
)


def _module_for_file(filename: str) -> str | None:
    """Derive the expected ABP module from an EDGE filename."""
    for prefix, module in FILE_MODULE_MAP.items():
        if filename.startswith(prefix):
            return module
    return None


def _extract_abp_json(html: str) -> str | None:
    """Extract the raw JSON string from an embedded ABP script block."""
    m = _ABP_PATTERN.search(html)
    return m.group(1).strip() if m else None


def check_file(
    filepath: Path,
    abp_ref: dict | None = None,
) -> list[tuple[str, bool, str]]:
    """Run all gate checks on a single EDGE HTML file.

    Returns list of (check_name, passed, detail) tuples.
    """
    checks: list[tuple[str, bool, str]] = []
    html = filepath.read_text(encoding="utf-8")
    filename = filepath.name

    # 1. ABP present
    raw_json = _extract_abp_json(html)
    if not raw_json:
        checks.append(("gate.abp_present", False, "No <script id=\"ds-abp-v1\"> block found"))
        return checks
    checks.append(("gate.abp_present", True, "<script id=\"ds-abp-v1\"> found"))

    # 2. JSON valid
    try:
        abp = json.loads(raw_json)
    except json.JSONDecodeError as e:
        checks.append(("gate.abp_json_valid", False, f"JSON parse error: {e}"))
        return checks
    checks.append(("gate.abp_json_valid", True, f"Valid JSON ({len(abp)} fields)"))

    # 3. Hash integrity
    computed_hash = _compute_abp_hash(abp)
    hash_ok = computed_hash == abp.get("hash", "")
    checks.append((
        "gate.abp_hash_integrity",
        hash_ok,
        f"{computed_hash[:30]}... verified" if hash_ok else f"mismatch: expected {abp.get('hash', 'n/a')[:30]}...",
    ))

    # 4. ID deterministic
    computed_id = _compute_abp_id(abp["scope"], abp["authority_ref"], abp["created_at"])
    id_ok = computed_id == abp.get("abp_id", "")
    checks.append((
        "gate.abp_id_deterministic",
        id_ok,
        f"{computed_id} verified" if id_ok else f"expected {abp.get('abp_id', 'n/a')}, got {computed_id}",
    ))

    # 5. No contradictions
    obj_a = {o["id"] for o in abp.get("objectives", {}).get("allowed", [])}
    obj_d = {o["id"] for o in abp.get("objectives", {}).get("denied", [])}
    tool_a = {t["name"] for t in abp.get("tools", {}).get("allow", [])}
    tool_d = {t["name"] for t in abp.get("tools", {}).get("deny", [])}
    obj_overlap = obj_a & obj_d
    tool_overlap = tool_a & tool_d
    no_contradictions = not obj_overlap and not tool_overlap
    detail = "No contradictions"
    if not no_contradictions:
        parts = []
        if obj_overlap:
            parts.append(f"objectives: {obj_overlap}")
        if tool_overlap:
            parts.append(f"tools: {tool_overlap}")
        detail = "; ".join(parts)
    checks.append(("gate.abp_no_contradictions", no_contradictions, detail))

    # 6. Reference match (if provided)
    if abp_ref is not None:
        ref_match = abp.get("hash") == abp_ref.get("hash")
        checks.append((
            "gate.abp_ref_match",
            ref_match,
            "Hash matches reference abp_v1.json" if ref_match else "Hash DIFFERS from reference",
        ))

    # 7. Module in scope
    module = _module_for_file(filename)
    if module:
        modules = abp.get("scope", {}).get("modules", [])
        in_scope = module in modules
        checks.append((
            "gate.module_in_scope",
            in_scope,
            f"{module} IN SCOPE" if in_scope else f"{module} NOT IN SCOPE (modules: {modules})",
        ))

    # 8. Status bar present
    has_bar = 'id="abpStatusBar"' in html or "id='abpStatusBar'" in html
    checks.append((
        "gate.status_bar_present",
        has_bar,
        '<div id="abpStatusBar"> found' if has_bar else "No status bar element found",
    ))

    # 9. Verification JS present
    has_js = "abpSelfVerify" in html
    checks.append((
        "gate.verification_js_present",
        has_js,
        "abpSelfVerify function found" if has_js else "No abpSelfVerify function found",
    ))

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ABP Gate — host-level enforcement for EDGE exports"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Check a single EDGE HTML file")
    group.add_argument("--dir", type=Path, help="Check all EDGE_*.html files in directory")
    parser.add_argument("--abp-ref", type=Path, default=None,
                        help="Reference abp_v1.json to compare against")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as failures")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Output results as JSON")
    args = parser.parse_args()

    # Load reference ABP if provided
    abp_ref = None
    if args.abp_ref:
        if not args.abp_ref.exists():
            print(f"ERROR: Reference ABP not found: {args.abp_ref}", file=sys.stderr)
            return 2
        abp_ref = json.loads(args.abp_ref.read_text())

    # Collect files
    files: list[Path] = []
    if args.file:
        if not args.file.exists():
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            return 2
        files = [args.file]
    else:
        if not args.dir.is_dir():
            print(f"ERROR: Directory not found: {args.dir}", file=sys.stderr)
            return 2
        files = sorted(args.dir.glob("EDGE_*.html"))
        if not files:
            print(f"ERROR: No EDGE_*.html files found in {args.dir}", file=sys.stderr)
            return 2

    # Run checks
    all_results: dict[str, list[tuple[str, bool, str]]] = {}
    total_checks = 0
    total_passed = 0
    total_failed = 0

    for f in files:
        checks = check_file(f, abp_ref)
        all_results[f.name] = checks
        for _, passed, _ in checks:
            total_checks += 1
            if passed:
                total_passed += 1
            else:
                total_failed += 1

    # Output
    if args.json_output:
        output = {
            "files": {
                name: [{"check": c, "pass": p, "detail": d} for c, p, d in checks]
                for name, checks in all_results.items()
            },
            "summary": {
                "total_files": len(files),
                "total_checks": total_checks,
                "passed": total_passed,
                "failed": total_failed,
                "result": "PASS" if total_failed == 0 else "FAIL",
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 60)
        print("  ABP Gate Enforcement Report")
        print("=" * 60)
        for name, checks in all_results.items():
            print(f"\n  -- {name} --")
            for check_name, passed, detail in checks:
                icon = "PASS" if passed else "FAIL"
                print(f"  [{icon}] {check_name}: {detail}")
        print()
        print("-" * 60)
        if total_failed == 0:
            print(f"  RESULT: ALL GATES PASSED  ({total_passed}/{total_checks} checks across {len(files)} files)")
        else:
            print(f"  RESULT: GATE FAILED  ({total_failed} failures, {total_passed} passed across {len(files)} files)")
        print("=" * 60)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
