#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    outdir = ROOT / "release_kpis"
    outdir.mkdir(parents=True, exist_ok=True)

    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    manual = outdir / f"kpi_{version}.json"
    if not manual.exists():
        raise SystemExit(f"Missing {manual}. Create it first.")

    # Merge telemetry into kpi_{version}_merged.json.
    subprocess.check_call(["python", "scripts/kpi_merge.py"])
    merged = outdir / f"kpi_{version}_merged.json"

    # Render radar + badge from merged values.
    subprocess.check_call(
        [
            "python",
            "scripts/render_radar.py",
            "--kpi",
            str(merged),
            "--outdir",
            "release_kpis",
        ]
    )
    subprocess.check_call(
        [
            "python",
            "scripts/render_badge.py",
            "--kpi",
            str(merged),
            "--out",
            "release_kpis/badge_latest.svg",
        ]
    )

    # Gate + history update.
    subprocess.check_call(["python", "scripts/kpi_gate.py"])

    radar_png = f"release_kpis/radar_{version}.png"
    radar_svg = f"release_kpis/radar_{version}.svg"
    badge_svg = "release_kpis/badge_latest.svg"

    comment = f"""## Repo Radar KPI — {version}

![badge]({badge_svg})

**Radar:**
- PNG: `{radar_png}`
- SVG: `{radar_svg}`

**KPI Gate:**
- `release_kpis/KPI_GATE_REPORT.md`

**Notes:**
- Some KPIs are auto-derived from repo telemetry (tests, docs, workflows, pilot drills).
- Manual KPIs remain for judgment-based areas (Authority, Scalability, Economic Measurability).
"""
    (outdir / "PR_COMMENT.md").write_text(comment, encoding="utf-8")
    print("Wrote: release_kpis/PR_COMMENT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
