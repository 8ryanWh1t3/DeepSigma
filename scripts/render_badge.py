#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SVG_TEMPLATE = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"320\" height=\"36\" role=\"img\" aria-label=\"{label}\">
  <linearGradient id=\"g\" x2=\"0\" y2=\"100%\">
    <stop offset=\"0\" stop-color=\"#fff\" stop-opacity=\".14\"/>
    <stop offset=\"1\" stop-color=\"#000\" stop-opacity=\".12\"/>
  </linearGradient>
  <rect rx=\"8\" width=\"320\" height=\"36\" fill=\"#111\"/>
  <rect rx=\"8\" x=\"112\" width=\"208\" height=\"36\" fill=\"{right}\"/>
  <rect rx=\"8\" width=\"320\" height=\"36\" fill=\"url(#g)\"/>
  <g fill=\"#fff\" text-anchor=\"middle\" font-family=\"DejaVu Sans,Verdana,Geneva,sans-serif\" font-size=\"14\">
    <text x=\"56\" y=\"24\" fill=\"#fff\" opacity=\".92\">{left_text}</text>
    <text x=\"216\" y=\"24\" fill=\"#fff\" opacity=\".96\">{right_text}</text>
  </g>
</svg>
"""


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def color_for_score(score: float) -> str:
    # Simple scale: red->amber->green
    if score < 5:
        return "#B00020"
    if score < 7.5:
        return "#C47F00"
    return "#1F8B4C"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kpi", required=True, help="Path to kpi_vX.json")
    ap.add_argument("--out", default="release_kpis/badge_latest.svg")
    args = ap.parse_args()

    obj = json.loads(Path(args.kpi).read_text(encoding="utf-8"))
    version = obj["version"]
    vals = obj["values"]
    # average score
    scores = [float(v) for v in vals.values()]
    avg = sum(scores) / max(1, len(scores))
    avg = clamp(avg, 0, 10)

    right = color_for_score(avg)
    svg = SVG_TEMPLATE.format(
        label=f"Repo KPI {version}",
        left_text="Repo KPI",
        right_text=f"{version} • {avg:.1f}/10",
        right=right,
    )
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
