#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    outdir = ROOT / "release_kpis"
    outdir.mkdir(parents=True, exist_ok=True)

    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    kpi_json = outdir / f"kpi_{version}.json"
    if not kpi_json.exists():
        raise SystemExit(f"Missing {kpi_json}. Create it first.")

    # Render radar
    subprocess.check_call(["python", "scripts/render_radar.py", "--kpi", str(kpi_json), "--outdir", "release_kpis"])

    # Render badge_latest.svg
    subprocess.check_call(["python", "scripts/render_badge.py", "--kpi", str(kpi_json), "--out", "release_kpis/badge_latest.svg"])

    # PR comment (versioned, deterministic)
    radar_png = f"release_kpis/radar_{version}.png"
    radar_svg = f"release_kpis/radar_{version}.svg"
    badge_svg = "release_kpis/badge_latest.svg"

    comment = f"""## Repo Radar KPI — {version}

![badge]({badge_svg})

**KPI Vector (0–10):**
- Technical Completeness: 9
- Automation Depth: 7
- Authority Modeling: 6
- Enterprise Readiness: 4
- Scalability: 4
- Data Integration: 5
- Economic Measurability: 3
- Operational Maturity: 7

**Artifacts:**
- PNG: `{radar_png}`
- SVG: `{radar_svg}`
- Badge: `{badge_svg}`

**Interpretation (pilot):**
- Strong: Technical + Automation + Operational maturity
- Needs investment: Enterprise readiness + Scalability + Economic measurability
"""
    (outdir / "PR_COMMENT.md").write_text(comment, encoding="utf-8")
    print("Wrote: release_kpis/PR_COMMENT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
