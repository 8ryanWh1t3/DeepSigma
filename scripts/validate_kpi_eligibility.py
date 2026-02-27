#!/usr/bin/env python3
"""Validate KPI eligibility tiers — every KPI must have an explicit tier declaration."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RK = ROOT / "enterprise" / "release_kpis"


def current_version() -> str:
    return (RK / "VERSION.txt").read_text(encoding="utf-8").strip()


def main() -> int:
    version = current_version()
    merged_path = RK / f"kpi_{version}_merged.json"
    if not merged_path.exists():
        print(f"SKIP: {merged_path.name} not found (run `make kpi` first)")
        return 0

    merged = json.loads(merged_path.read_text(encoding="utf-8"))
    eligibility = merged.get("eligibility", {}).get("kpis", {})
    values = merged.get("values", {})

    if not eligibility:
        print("FAIL: no eligibility metadata in merged KPI")
        return 1

    warnings = 0
    failures = 0
    for kpi, info in sorted(eligibility.items()):
        tier = info.get("tier", "unknown")
        score = values.get(kpi, "?")
        cap = info.get("tier_cap", "?")
        if tier == "unverified":
            print(f"  [WARN] {kpi}: tier={tier} (score={score}, cap={cap})")
            warnings += 1
        elif tier == "simulated":
            print(f"  [INFO] {kpi}: tier={tier} (score={score}, cap={cap})")
        else:
            print(f"  [PASS] {kpi}: tier={tier} (score={score}, cap={cap})")

    total = len(eligibility)
    if failures:
        print(f"\nKPI eligibility validation FAILED ({failures} missing tiers)")
        return 1
    if warnings:
        print(f"\nKPI eligibility validation WARN ({warnings}/{total} unverified)")
    else:
        print(f"\nKPI eligibility validation PASSED ({total}/{total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
