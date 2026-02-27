#!/usr/bin/env python3
"""TEC Sensitivity & Variance Modeling — cost volatility, sensitivity bands, fragility score."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RK = ROOT / "release_kpis"
POLICY_PATH = ROOT / "governance" / "tec_ctec_policy.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def main() -> int:
    policy = load_json(POLICY_PATH)
    tiers = ["internal", "executive", "public_sector"]
    tec_data: dict[str, dict] = {}
    for tier in tiers:
        path = RK / f"tec_{tier}.json"
        if path.exists():
            tec_data[tier] = load_json(path)

    if not tec_data:
        print("SKIP: no TEC tier files found")
        return 0

    # Use first available tier for cost extraction.
    ref = next(iter(tec_data.values()))
    low_cost = float(ref["low"]["cost"])
    base_cost = float(ref["base"]["cost"])
    high_cost = float(ref["high"]["cost"])

    # 1) Cost volatility index: stddev of tier costs / mean.
    costs = [low_cost, base_cost, high_cost]
    mean_cost = sum(costs) / len(costs)
    variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
    stddev = math.sqrt(variance)
    cost_volatility_index = round(stddev / mean_cost if mean_cost else 0.0, 4)

    # 2) Spread ratio.
    spread_ratio = round((high_cost - low_cost) / base_cost if base_cost else 0.0, 4)

    # 3) Sensitivity bands: what happens to C-TEC if RCF/CCF shift by ±1 tier.
    rcf_map = policy.get("icr_rcf", {})
    ccf_map = policy.get("ccf_map", {})
    rcf_values = sorted(rcf_map.values())
    ccf_values = sorted(ccf_map.values())

    total_ctec = float(ref["total"]["ctec"])
    total_tec = float(ref["total"]["tec"])

    # Current factors.
    current_rcf = float(ref["total"].get("rcf", 1.0))
    current_ccf = float(ref["total"].get("ccf", 1.0))

    # RCF sensitivity: best and worst case.
    rcf_best = max(rcf_values) if rcf_values else 1.0
    rcf_worst = min(rcf_values) if rcf_values else 0.6
    ctec_rcf_best = round(total_tec * rcf_best * current_ccf, 2)
    ctec_rcf_worst = round(total_tec * rcf_worst * current_ccf, 2)

    # CCF sensitivity: best and worst case.
    ccf_best = max(ccf_values) if ccf_values else 1.0
    ccf_worst = min(ccf_values) if ccf_values else 0.7
    ctec_ccf_best = round(total_tec * current_rcf * ccf_best, 2)
    ctec_ccf_worst = round(total_tec * current_rcf * ccf_worst, 2)

    # Combined worst/best.
    ctec_combined_best = round(total_tec * rcf_best * ccf_best, 2)
    ctec_combined_worst = round(total_tec * rcf_worst * ccf_worst, 2)

    # 4) Economic fragility score: 0–100 (higher = more fragile / less stable).
    # Blend of spread ratio and sensitivity amplitude.
    sensitivity_amplitude = (ctec_combined_best - ctec_combined_worst) / total_ctec if total_ctec else 0.0
    fragility_raw = (0.5 * min(1.0, spread_ratio)) + (0.5 * min(1.0, sensitivity_amplitude))
    economic_fragility_score = round(clamp(fragility_raw * 100.0), 2)

    # Invert for "economic stability score" (0–100, higher = more stable).
    economic_stability_score = round(100.0 - economic_fragility_score, 2)

    result = {
        "schema": "tec_sensitivity_v1",
        "cost_volatility_index": cost_volatility_index,
        "spread_ratio": spread_ratio,
        "costs": {"low": low_cost, "base": base_cost, "high": high_cost},
        "sensitivity": {
            "rcf": {"best_ctec": ctec_rcf_best, "worst_ctec": ctec_rcf_worst},
            "ccf": {"best_ctec": ctec_ccf_best, "worst_ctec": ctec_ccf_worst},
            "combined": {"best_ctec": ctec_combined_best, "worst_ctec": ctec_combined_worst},
        },
        "current": {
            "total_tec": total_tec,
            "total_ctec": total_ctec,
            "rcf": current_rcf,
            "ccf": current_ccf,
        },
        "economic_fragility_score": economic_fragility_score,
        "economic_stability_score": economic_stability_score,
    }

    out_json = RK / "tec_sensitivity.json"
    out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    # Markdown report.
    lines = [
        "# TEC Sensitivity Report",
        "",
        f"## Cost Volatility Index: {cost_volatility_index}",
        f"- Spread ratio: {spread_ratio}",
        f"- Low: ${low_cost:,.0f} | Base: ${base_cost:,.0f} | High: ${high_cost:,.0f}",
        "",
        "## Sensitivity Bands",
        f"- RCF shift: C-TEC range [{ctec_rcf_worst:,.0f}, {ctec_rcf_best:,.0f}]",
        f"- CCF shift: C-TEC range [{ctec_ccf_worst:,.0f}, {ctec_ccf_best:,.0f}]",
        f"- Combined: C-TEC range [{ctec_combined_worst:,.0f}, {ctec_combined_best:,.0f}]",
        "",
        "## Economic Fragility",
        f"- Fragility score: **{economic_fragility_score}** / 100",
        f"- Stability score: **{economic_stability_score}** / 100",
        "",
    ]
    out_md = RK / "tec_sensitivity_report.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
