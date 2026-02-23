#!/usr/bin/env python3
import json
from pathlib import Path

CAT = Path("release_kpis/feature_catalog.json")
OUT = Path("docs/FEATURE_CATALOG.md")

def main():
    data = json.loads(CAT.read_text(encoding="utf-8"))

    lines = []
    lines.append("# DeepSigma Feature Catalog")
    lines.append("")
    lines.append("Machine source of truth: `release_kpis/feature_catalog.json`")
    lines.append("")
    lines.append("## Categories")
    lines.append("")

    for c in data["categories"]:
        lines.append(f"### {c['name']}\n{c['summary']}")
        lines.append("")
        for f in c["features"]:
            lines.append(f"- **{f['name']}** (`{f['id']}`)")
            lines.append(f"  - {f['description']}")
            if f.get("artifacts"):
                lines.append(f"  - Artifacts: {', '.join(f['artifacts'])}")
            if f.get("enforcement"):
                lines.append(f"  - Enforcement: {', '.join(f['enforcement'])}")
            if f.get("kpi_axes"):
                lines.append(f"  - KPI axes: {', '.join(f['kpi_axes'])}")
        lines.append("")

    lines.append("## Outer-Edge Boundaries")
    lines.append("")
    for b in data.get("outer_edge_boundaries", []):
        lines.append(f"- {b}")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("PASS: rendered docs/FEATURE_CATALOG.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
