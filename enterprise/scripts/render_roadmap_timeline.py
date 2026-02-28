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

    max_items = 8
    line_height = 22
    font_size = 14
    width = 1200
    baseline_y = 100
    spacing = 500 if len(versions) <= 2 else max(240, int((width - 240) / max(1, len(versions) - 1)))
    start_x = 230

    # Compute height from tallest item list
    max_bullet_count = max(min(len(p.get("scope") or p.get("focus") or []), max_items) for p in roadmap.values())
    box_h = 30 + (max_bullet_count * line_height)
    height = baseline_y + 40 + box_h + 30

    colors = {"active": "#1F8B4C", "released": "#2563EB", "dormant": "#C47F00", "planned": "#666"}

    circles = []
    labels = []
    boxes = []

    for idx, version in enumerate(versions):
        payload = roadmap[version]
        status = str(payload.get("status", "planned"))
        x = start_x + (idx * spacing)
        color = colors.get(status, colors["planned"])
        items = payload.get("scope") or payload.get("focus") or []
        display_items = items[:max_items]
        remaining = len(items) - max_items
        title = f"{version} ({status})"
        circles.append(f"<circle cx='{x}' cy='{baseline_y}' r='16' fill='{color}' />")
        labels.append(f"<text x='{x}' y='{baseline_y - 26}' text-anchor='middle' font-size='16' font-weight='bold' fill='#111'>{title}</text>")
        labels.append(f"<text x='{x}' y='{baseline_y + 5}' text-anchor='middle' font-size='13' fill='#fff'>{idx + 1}</text>")

        box_y = baseline_y + 40
        box_w = 400
        box_x = x - (box_w // 2)
        bullet_lines = "".join(
            f"<text x='{box_x + 14}' y='{box_y + 24 + (line_idx * line_height)}' font-size='{font_size}' fill='#111'>- {text}</text>"
            for line_idx, text in enumerate(display_items)
        )
        if remaining > 0:
            bullet_lines += f"<text x='{box_x + 14}' y='{box_y + 24 + (len(display_items) * line_height)}' font-size='{font_size}' fill='#888'>  +{remaining} more</text>"
        boxes.append(
            f"<rect x='{box_x}' y='{box_y}' width='{box_w}' height='{box_h}' rx='8' fill='#f5f7fb' stroke='#d4d8e3'/>"
            + bullet_lines
        )

    connectors = []
    for idx in range(len(versions) - 1):
        x1 = start_x + (idx * spacing)
        x2 = start_x + ((idx + 1) * spacing)
        connectors.append(f"<line x1='{x1 + 16}' y1='{baseline_y}' x2='{x2 - 16}' y2='{baseline_y}' stroke='#222' stroke-width='3' />")

    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' role='img' aria-label='Roadmap timeline'>"
        "<rect width='100%' height='100%' fill='#fff'/>"
        "<text x='30' y='36' font-size='24' font-family='DejaVu Sans,Verdana,sans-serif' font-weight='bold' fill='#111'>DeepSigma Roadmap Timeline</text>"
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
