#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "roadmap" / "roadmap.json"
OUT_PATH = ROOT / "release_kpis" / "roadmap_badge.svg"

SVG = """<svg xmlns='http://www.w3.org/2000/svg' width='420' height='36' role='img' aria-label='{label}'>
  <rect rx='8' width='420' height='36' fill='#111'/>
  <rect rx='8' x='128' width='292' height='36' fill='{color}'/>
  <g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,sans-serif' font-size='14'>
    <text x='64' y='24'>Roadmap</text>
    <text x='274' y='24'>{text}</text>
  </g>
</svg>
"""


def main() -> int:
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    active = [v for v, payload in roadmap.items() if payload.get("status") == "active"]
    dormant = [v for v, payload in roadmap.items() if payload.get("status") == "dormant"]

    active_text = active[0] if active else "none"
    next_text = dormant[0] if dormant else "none"
    text = f"active {active_text} • next {next_text}"
    color = "#1F8B4C" if active else "#B00020"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        SVG.format(label=f"Roadmap {text}", text=text, color=color),
        encoding="utf-8",
    )
    print(f"Wrote: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
