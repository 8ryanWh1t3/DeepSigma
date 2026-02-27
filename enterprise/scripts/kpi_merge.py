#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    outdir = ROOT / "release_kpis"
    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    manual_path = outdir / f"kpi_{version}.json"
    if not manual_path.exists():
        raise SystemExit(f"Missing manual KPI file: {manual_path}")

    manual = json.loads(manual_path.read_text(encoding="utf-8"))
    values = dict(manual.get("values", {}))

    telemetry = json.loads(
        subprocess.check_output(["python", "enterprise/scripts/kpi_compute.py"], text=True)
    )

    for key, value in telemetry.items():
        if key.startswith("_"):
            continue
        values[key] = float(value)

    issue_path = outdir / "issue_deltas.json"
    if issue_path.exists():
        issue = json.loads(issue_path.read_text(encoding="utf-8"))
        for key, delta in issue.get("kpis", {}).items():
            if key not in values:
                continue
            values[key] = (
                float(values[key])
                + float(delta.get("credit_delta", 0))
                - float(delta.get("debt_delta", 0))
            )
            cap = delta.get("cap_if_open_p0")
            if cap is not None:
                values[key] = min(values[key], float(cap))

    for key in list(values.keys()):
        values[key] = max(0, min(10, float(values[key])))

    # Apply artifact eligibility tiers so KPI claims are capped by evidence.
    eligibility_path = ROOT / "governance" / "kpi_eligibility.json"
    eligibility_rules = json.loads(eligibility_path.read_text(encoding="utf-8"))
    tier_order = eligibility_rules.get(
        "tier_order", ["unverified", "simulated", "real", "production"]
    )
    tier_meta = eligibility_rules.get("tiers", {})

    kpi_eligibility: dict[str, dict] = {}
    for key, raw_value in list(values.items()):
        rule = eligibility_rules.get("kpis", {}).get(key, {})
        achieved_tier = "unverified"
        missing_by_tier: dict[str, list[str]] = {}

        for tier in ("simulated", "real", "production"):
            required = [str(path) for path in rule.get(tier, [])]
            missing = [path for path in required if not (ROOT / path).exists()]
            missing_by_tier[tier] = missing
            if not missing:
                achieved_tier = tier
            else:
                break

        tier_cap = float(tier_meta.get(achieved_tier, {}).get("max_score", 3.0))
        confidence = float(tier_meta.get(achieved_tier, {}).get("confidence", 0.30))
        capped_value = min(float(raw_value), tier_cap)
        values[key] = round(max(0.0, min(10.0, capped_value)), 2)
        kpi_eligibility[key] = {
            "tier": achieved_tier,
            "tier_cap": tier_cap,
            "confidence": round(confidence, 3),
            "missing_by_tier": missing_by_tier,
        }

    merged = {
        "version": version,
        "scale": manual.get("scale", {"min": 0, "max": 10}),
        "values": values,
        "telemetry": telemetry.get("_telemetry", {}),
        "eligibility": {
            "schema": eligibility_rules.get("schema", "kpi_eligibility_v1"),
            "tier_order": tier_order,
            "kpis": kpi_eligibility,
        },
    }

    merged_path = outdir / f"kpi_{version}_merged.json"
    merged_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote: {merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
