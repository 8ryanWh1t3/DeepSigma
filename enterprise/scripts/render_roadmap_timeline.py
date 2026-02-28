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

    # Vertical layout — keeps SVG close to GitHub's ~800px container so text stays large
    max_items = 12
    line_height = 32
    font_size = 22
    width = 880
    margin_x = 40
    box_w = width - (margin_x * 2)
    title_y = 50
    section_gap = 30

    colors = {"active": "#1F8B4C", "released": "#2563EB", "dormant": "#C47F00", "planned": "#666"}

    elements: list[str] = []
    cursor_y = title_y + 40  # after main title

    for idx, version in enumerate(versions):
        payload = roadmap[version]
        status = str(payload.get("status", "planned"))
        color = colors.get(status, colors["planned"])
        items = payload.get("scope") or payload.get("focus") or []
        display_items = items[:max_items]
        remaining = len(items) - max_items
        heading = f"{version}  —  {status}"

        # Connector dot + vertical line between sections
        if idx > 0:
            elements.append(f"<line x1='{width // 2}' y1='{cursor_y - section_gap}' x2='{width // 2}' y2='{cursor_y}' stroke='#222' stroke-width='4' />")
        dot_y = cursor_y + 16
        elements.append(f"<circle cx='{width // 2}' cy='{dot_y}' r='14' fill='{color}' />")
        elements.append(f"<text x='{width // 2}' y='{dot_y + 6}' text-anchor='middle' font-size='14' fill='#fff'>{idx + 1}</text>")

        # Version heading
        heading_y = dot_y + 40
        elements.append(f"<text x='{width // 2}' y='{heading_y}' text-anchor='middle' font-size='26' font-weight='bold' fill='#111'>{heading}</text>")

        # Scope box
        box_y = heading_y + 14
        n_lines = len(display_items) + (1 if remaining > 0 else 0)
        box_h = 20 + (n_lines * line_height) + 10
        elements.append(f"<rect x='{margin_x}' y='{box_y}' width='{box_w}' height='{box_h}' rx='10' fill='#f5f7fb' stroke='#d4d8e3' stroke-width='2'/>")
        for line_idx, text in enumerate(display_items):
            elements.append(
                f"<text x='{margin_x + 20}' y='{box_y + 20 + line_height // 2 + (line_idx * line_height)}' font-size='{font_size}' fill='#111'>• {text}</text>"
            )
        if remaining > 0:
            elements.append(
                f"<text x='{margin_x + 20}' y='{box_y + 20 + line_height // 2 + (len(display_items) * line_height)}' font-size='{font_size}' fill='#888'>  +{remaining} more</text>"
            )

        cursor_y = box_y + box_h + section_gap

    height = cursor_y + 20

    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' role='img' aria-label='Roadmap timeline'>"
        "<rect width='100%' height='100%' fill='#fff'/>"
        f"<text x='{width // 2}' y='{title_y}' text-anchor='middle' font-size='30' font-family='DejaVu Sans,Verdana,sans-serif' font-weight='bold' fill='#111'>DeepSigma Roadmap Timeline</text>"
        + "".join(elements)
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
