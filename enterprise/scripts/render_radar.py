#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "governance" / "kpi_spec.yaml"


def read_spec() -> List[Tuple[str, str]]:
    # Minimal YAML reader without external deps:
    # We only need ordered kpis key/label. This parser assumes the spec format above.
    text = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    out: List[Tuple[str, str]] = []
    cur_key = None
    cur_label = None
    for line in text:
        s = line.strip()
        if s.startswith("- key:"):
            cur_key = s.split(":", 1)[1].strip()
            cur_label = None
        elif s.startswith("label:") and cur_key:
            cur_label = s.split(":", 1)[1].strip().strip('"').strip("'")
            out.append((cur_key, cur_label))
            cur_key, cur_label = None, None
    if len(out) != 8:
        raise SystemExit(f"Expected 8 KPIs in spec; got {len(out)}")
    return out


def read_kpis(kpi_json: Path) -> Tuple[str, Dict[str, float]]:
    obj = json.loads(kpi_json.read_text(encoding="utf-8"))
    version = obj["version"]
    values = obj["values"]
    return version, {k: float(v) for k, v in values.items()}


def render_radar(
    version: str,
    labels: List[str],
    values: List[float],
    out_png: Path,
    out_svg: Path,
    bands_low: List[float] | None = None,
    bands_high: List[float] | None = None,
) -> None:
    n = len(labels)
    angles = [2 * math.pi * i / n for i in range(n)]
    angles += angles[:1]
    vals = values + values[:1]

    fig = plt.figure(figsize=(8, 6), dpi=140)
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_rlabel_position(90)
    ax.set_ylim(0, 10)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8)

    # Confidence band envelope (if provided).
    if bands_low is not None and bands_high is not None:
        lo = bands_low + bands_low[:1]
        hi = bands_high + bands_high[:1]
        ax.fill_between(angles, lo, hi, alpha=0.10, color="orange", label="Confidence band")

    ax.plot(angles, vals, linewidth=2)
    ax.fill(angles, vals, alpha=0.20)

    title_suffix = " (banded)" if bands_low is not None else ""
    ax.set_title(f"Repo KPI Radar — {version}{title_suffix}", y=1.14, fontsize=14, fontweight="bold")
    fig.text(0.5, 0.02, "Scale: 0–10 (rings at 2/4/6/8/10)", ha="center", fontsize=8)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kpi", required=True, help="Path to kpi_vX.json")
    ap.add_argument("--outdir", default="release_kpis", help="Output directory")
    args = ap.parse_args()

    spec = read_spec()
    version, vals = read_kpis(Path(args.kpi))
    labels = [label for _, label in spec]
    values = []
    for key, _label in spec:
        if key not in vals:
            raise SystemExit(f"Missing KPI value for '{key}' in {args.kpi}")
        v = float(vals[key])
        if v < 0 or v > 10:
            raise SystemExit(f"KPI '{key}' out of range 0–10: {v}")
        values.append(v)

    outdir = ROOT / args.outdir
    out_png = outdir / f"radar_{version}.png"
    out_svg = outdir / f"radar_{version}.svg"
    render_radar(version, labels, values, out_png, out_svg)
    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_svg}")

    # Banded radar: render with confidence bands if available.
    bands_path = outdir / f"kpi_bands_{version}.json"
    if bands_path.exists():
        bands = json.loads(bands_path.read_text(encoding="utf-8"))
        bands_data = bands.get("bands", {})
        lo_vals: List[float] = []
        hi_vals: List[float] = []
        for key, _label in spec:
            b = bands_data.get(key, {})
            lo_vals.append(max(0.0, float(b.get("low", vals.get(key, 0)))))
            hi_vals.append(min(10.0, float(b.get("high", vals.get(key, 0)))))
        bands_png = outdir / f"radar_{version}_bands.png"
        bands_svg = outdir / f"radar_{version}_bands.svg"
        render_radar(version, labels, values, bands_png, bands_svg, lo_vals, hi_vals)
        print(f"Wrote: {bands_png}")
        print(f"Wrote: {bands_svg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
