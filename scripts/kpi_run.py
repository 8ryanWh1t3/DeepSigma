#!/usr/bin/env python3
from __future__ import annotations

import json
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
    subprocess.check_call(["python", "scripts/render_kpi_trend.py"])
    subprocess.check_call(["python", "scripts/render_composite_radar.py"])
    subprocess.check_call(["make", "tec"])

    radar_png = f"release_kpis/radar_{version}.png"
    radar_svg = f"release_kpis/radar_{version}.svg"
    badge_svg = "release_kpis/badge_latest.svg"
    tec_internal = outdir / "tec_internal.json"
    tec_executive = outdir / "tec_executive.json"
    tec_dod = outdir / "tec_dod.json"
    if not (tec_internal.exists() and tec_executive.exists() and tec_dod.exists()):
        raise SystemExit("Missing TEC artifacts. Expected tec_internal/executive/dod json files.")
    tec_internal_data = json.loads(tec_internal.read_text(encoding="utf-8"))
    tec_executive_data = json.loads(tec_executive.read_text(encoding="utf-8"))
    tec_dod_data = json.loads(tec_dod.read_text(encoding="utf-8"))

    comment = f"""## Repo Radar KPI — {version}

![badge]({badge_svg})

**Radar:**
- PNG: `{radar_png}`
- SVG: `{radar_svg}`

**Composite Release Radar:**
- PNG: `release_kpis/radar_composite_latest.png`
- SVG: `release_kpis/radar_composite_latest.svg`
- Delta table: `release_kpis/radar_composite_latest.md`

**Trend:**
- PNG: `release_kpis/kpi_trend.png`
- SVG: `release_kpis/kpi_trend.svg`

**Gates:**
- `release_kpis/KPI_GATE_REPORT.md`
- `release_kpis/ISSUE_LABEL_GATE_REPORT.md`

**TEC (ROM):**
- Internal: {tec_internal_data["base"]["hours"]} hrs | ${int(tec_internal_data["base"]["cost"]):,}
- Executive: {tec_executive_data["base"]["hours"]} hrs | ${int(tec_executive_data["base"]["cost"]):,}
- DoD: {tec_dod_data["base"]["hours"]} hrs | ${int(tec_dod_data["base"]["cost"]):,}
- Full detail: `release_kpis/TEC_SUMMARY.md`

**Notes:**
- Some KPIs are auto-derived from repo telemetry (tests, docs, workflows, pilot drills).
- Economic and Scalability are auto-derived from DISR metrics and capped by evidence eligibility (`kpi_eligible` / `evidence_level`).
- Authority Modeling remains manual/judgment-based until authority telemetry scoring is wired.
"""
    (outdir / "PR_COMMENT.md").write_text(comment, encoding="utf-8")
    print("Wrote: release_kpis/PR_COMMENT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
