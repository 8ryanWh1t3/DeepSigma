#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def format_layer_coverage() -> str:
    mapping_path = ROOT / "release_kpis" / "layer_kpi_mapping.json"
    if not mapping_path.exists():
        return ""

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    lines = ["", "**Layer Coverage (Decision Infrastructure):**"]
    for layer, kpis in mapping.items():
        if isinstance(kpis, list):
            kpi_str = ", ".join(kpis)
        else:
            kpi_str = str(kpis)
        lines.append(f"- {layer}: {kpi_str}")
    return "\n".join(lines)


def append_feature_coverage_to_pr_comment(pr_comment_path: str = "release_kpis/PR_COMMENT.md") -> None:
    cat_path = ROOT / "release_kpis" / "feature_catalog.json"
    if not cat_path.exists():
        return

    data = json.loads(cat_path.read_text(encoding="utf-8"))
    lines = []
    lines.append("")
    lines.append("## 🧩 Feature Coverage (Catalog)")
    for category in data.get("categories", []):
        lines.append(
            f"- **{category.get('name', '(unnamed)')}**: {len(category.get('features', []))} features"
        )

    out_path = ROOT / pr_comment_path
    if out_path.exists():
        out_path.write_text(out_path.read_text(encoding="utf-8") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


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
    merged_data = json.loads(merged.read_text(encoding="utf-8"))

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
    subprocess.check_call(["python", "scripts/kpi_confidence_bands.py"])

    # Gate + history update.  Run gate first but defer failure so remaining
    # artifacts (trend, radar, roadmap, stability, tec) are still generated.
    gate_result = subprocess.run(["python", "scripts/kpi_gate.py"])
    subprocess.check_call(["python", "scripts/render_kpi_trend.py"])
    subprocess.check_call(["python", "scripts/render_composite_radar.py"])
    subprocess.check_call(["make", "roadmap-refresh"], cwd=REPO_ROOT)
    subprocess.check_call(["make", "stability"], cwd=REPO_ROOT)
    subprocess.check_call(["make", "tec"], cwd=REPO_ROOT)

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
    telemetry = merged_data.get("telemetry", {})
    insights = telemetry.get("insights", {})
    insights_section = ""
    if isinstance(insights, dict) and insights.get("present"):
        score = insights.get("score")
        score_text = "n/a" if score is None else f"{float(score):.2f}/10"
        signal_count = int(insights.get("signals", 0))
        source = str(insights.get("source", "release_kpis/insights_metrics.json"))
        insights_section = (
            "\n"
            "**Insights Metrics:**\n"
            f"- Score: {score_text}\n"
            f"- Signals: {signal_count}\n"
            f"- Source: `{source}`\n"
        )
    else:
        insights_section = (
            "\n"
            "**Insights Metrics:**\n"
            "- Not present (`release_kpis/insights_metrics.json` not found)\n"
        )
    layer_coverage = format_layer_coverage()

    comment = f"""## Repo Radar KPI — {version}

![badge]({badge_svg})

**Radar:**
- PNG: `{radar_png}`
- SVG: `{radar_svg}`

**Composite Release Radar:**
- PNG: `release_kpis/radar_composite_latest.png`
- SVG: `release_kpis/radar_composite_latest.svg`
- Delta table: `release_kpis/radar_composite_latest.md`

**Roadmap Forecast:**
- Badge: `release_kpis/roadmap_badge.svg`
- Forecast: `release_kpis/roadmap_forecast.md`
- Timeline: `release_kpis/roadmap_timeline.svg`
- Scope gate: `release_kpis/ROADMAP_SCOPE_GATE_REPORT.md`

**Nonlinear Stability:**
- SSI JSON: `release_kpis/stability_{version}.json`
- Simulation: `release_kpis/stability_simulation_{version}.json`
- Report: `release_kpis/nonlinear_stability_report.md`

**Trend:**
- PNG: `release_kpis/kpi_trend.png`
- SVG: `release_kpis/kpi_trend.svg`

**Gates:**
- `release_kpis/KPI_GATE_REPORT.md`
- `release_kpis/ISSUE_LABEL_GATE_REPORT.md`

**Eligibility + Confidence:**
- Eligibility tiers: `governance/kpi_eligibility.json`
- KPI confidence: `release_kpis/kpi_confidence.json`
- KPI bands: `release_kpis/kpi_bands_{version}.json`

**TEC (ROM):**
- Internal: {tec_internal_data["base"]["hours"]} hrs | ${int(tec_internal_data["base"]["cost"]):,}
- Executive: {tec_executive_data["base"]["hours"]} hrs | ${int(tec_executive_data["base"]["cost"]):,}
- DoD: {tec_dod_data["base"]["hours"]} hrs | ${int(tec_dod_data["base"]["cost"]):,}
- Full detail: `release_kpis/TEC_SUMMARY.md`

**Notes:**
- Some KPIs are auto-derived from repo telemetry (tests, docs, workflows, pilot drills).
- Economic and Scalability are auto-derived from DISR metrics and capped by evidence eligibility (`kpi_eligible` / `evidence_level`).
- Authority Modeling remains manual/judgment-based until authority telemetry scoring is wired.
{insights_section}
{layer_coverage}
"""
    (outdir / "PR_COMMENT.md").write_text(comment, encoding="utf-8")
    append_feature_coverage_to_pr_comment()
    print("Wrote: release_kpis/PR_COMMENT.md")
    return gate_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
