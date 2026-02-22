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
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    items: List[Tuple[str, str]] = []
    current_key: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- key:"):
            current_key = stripped.split(":", 1)[1].strip()
        elif current_key and stripped.startswith("label:"):
            label = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            items.append((current_key, label))
            current_key = None
    if len(items) != 8:
        raise SystemExit(f"Expected 8 KPIs in spec; got {len(items)}")
    return items


def load_history(history_path: Path) -> List[Dict]:
    if not history_path.exists():
        raise SystemExit(f"Missing history file: {history_path}")
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not entries:
        raise SystemExit("No KPI history entries found")
    return entries


def normalize_values(entries: List[Dict], keys: List[str]) -> List[Tuple[str, List[float]]]:
    vectors: List[Tuple[str, List[float]]] = []
    for entry in entries:
        version = str(entry.get("version", "unknown"))
        values = entry.get("values", {})
        vector: List[float] = []
        for key in keys:
            value = float(values.get(key, 0.0))
            vector.append(max(0.0, min(10.0, value)))
        vectors.append((version, vector))
    return vectors


def render_overlay(labels: List[str], vectors: List[Tuple[str, List[float]]], out_png: Path, out_svg: Path) -> None:
    count = len(labels)
    angles = [2 * math.pi * idx / count for idx in range(count)]
    angles += angles[:1]

    fig = plt.figure(figsize=(9, 7), dpi=140)
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(90)
    ax.set_ylim(0, 10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8)

    palette = ["#1F77B4", "#2CA02C", "#D62728", "#FF7F0E", "#9467BD"]
    for idx, (version, vector) in enumerate(vectors):
        values = vector + vector[:1]
        color = palette[idx % len(palette)]
        alpha = 0.12 + (0.08 * idx)
        ax.plot(angles, values, linewidth=2, color=color, label=version)
        ax.fill(angles, values, color=color, alpha=min(alpha, 0.35))

    ax.set_title("Repo KPI Composite Radar (Release Comparison)", y=1.15, fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.1), frameon=False, fontsize=8)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def write_delta_summary(keys: List[str], labels: Dict[str, str], vectors: List[Tuple[str, List[float]]], out_md: Path) -> None:
    latest_version, latest_values = vectors[-1]
    lines = [
        "# Composite Release Comparison",
        "",
        f"Latest release: `{latest_version}`",
        "",
    ]

    if len(vectors) >= 2:
        prev_version, prev_values = vectors[-2]
        lines.append(f"Compared to previous release: `{prev_version}`")
        lines.append("")
        lines.append("| KPI | Previous | Latest | Delta |")
        lines.append("|---|---:|---:|---:|")
        for idx, key in enumerate(keys):
            delta = latest_values[idx] - prev_values[idx]
            lines.append(
                f"| {labels[key]} | {prev_values[idx]:.2f} | {latest_values[idx]:.2f} | {delta:+.2f} |"
            )
    else:
        lines.append("Only one release in history; no previous release available for delta comparison.")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--history", default="release_kpis/history.json", help="KPI history JSON path")
    parser.add_argument("--outdir", default="release_kpis", help="Output directory")
    parser.add_argument("--window", type=int, default=3, help="Number of latest releases to overlay")
    args = parser.parse_args()

    spec = read_spec()
    keys = [key for key, _ in spec]
    labels = {key: label for key, label in spec}

    history_entries = load_history(ROOT / args.history)
    window = max(2, args.window)
    recent = history_entries[-window:]
    vectors = normalize_values(recent, keys)

    display_labels = [labels[key] for key in keys]
    outdir = ROOT / args.outdir
    out_png = outdir / "radar_composite_latest.png"
    out_svg = outdir / "radar_composite_latest.svg"
    out_md = outdir / "radar_composite_latest.md"

    render_overlay(display_labels, vectors, out_png, out_svg)
    write_delta_summary(keys, labels, vectors, out_md)

    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_svg}")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
