#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "roadmap" / "roadmap.json"
OUT_SVG = ROOT / "release_kpis" / "roadmap_timeline.svg"
OUT_MD = ROOT / "release_kpis" / "roadmap_timeline.md"


def main() -> int:
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    versions = list(roadmap.keys())

    width = 980
    height = 220
    baseline_y = 80
    spacing = 380 if len(versions) <= 2 else max(180, int((width - 180) / max(1, len(versions) - 1)))
    start_x = 120

    colors = {"active": "#1F8B4C", "dormant": "#C47F00", "planned": "#666"}

    circles = []
    labels = []
    boxes = []

    for idx, version in enumerate(versions):
        payload = roadmap[version]
        status = str(payload.get("status", "planned"))
        x = start_x + (idx * spacing)
        color = colors.get(status, colors["planned"])
        items = payload.get("scope") or payload.get("focus") or []
        title = f"{version} ({status})"
        circles.append(f"<circle cx='{x}' cy='{baseline_y}' r='14' fill='{color}' />")
        labels.append(f"<text x='{x}' y='{baseline_y - 20}' text-anchor='middle' font-size='14' fill='#111'>{title}</text>")
        labels.append(f"<text x='{x}' y='{baseline_y + 5}' text-anchor='middle' font-size='12' fill='#fff'>{idx + 1}</text>")

        box_y = 120
        box_w = 280
        box_h = 86
        box_x = x - (box_w // 2)
        bullet_lines = "".join(
            f"<text x='{box_x + 10}' y='{box_y + 20 + (line_idx * 16)}' font-size='12' fill='#111'>- {text}</text>"
            for line_idx, text in enumerate(items[:4])
        )
        boxes.append(
            f"<rect x='{box_x}' y='{box_y}' width='{box_w}' height='{box_h}' rx='8' fill='#f5f7fb' stroke='#d4d8e3'/>"
            + bullet_lines
        )

    connectors = []
    for idx in range(len(versions) - 1):
        x1 = start_x + (idx * spacing)
        x2 = start_x + ((idx + 1) * spacing)
        connectors.append(f"<line x1='{x1 + 14}' y1='{baseline_y}' x2='{x2 - 14}' y2='{baseline_y}' stroke='#222' stroke-width='2' />")

    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' role='img' aria-label='Roadmap timeline'>"
        "<rect width='100%' height='100%' fill='#fff'/>"
        "<text x='20' y='28' font-size='20' font-family='DejaVu Sans,Verdana,sans-serif' fill='#111'>DeepSigma Roadmap Timeline</text>"
        + "".join(connectors)
        + "".join(circles)
        + "".join(labels)
        + "".join(boxes)
        + "</svg>"
    )

    OUT_SVG.parent.mkdir(parents=True, exist_ok=True)
    OUT_SVG.write_text(svg, encoding="utf-8")

    lines = ["# Roadmap Timeline", "", f"![Roadmap Timeline]({OUT_SVG.name})", ""]
    for version in versions:
        payload = roadmap[version]
        lines.append(f"## {version} ({payload.get('status', 'planned')})")
        for item in payload.get("scope", payload.get("focus", [])):
            lines.append(f"- {item}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {OUT_SVG}")
    print(f"Wrote: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
