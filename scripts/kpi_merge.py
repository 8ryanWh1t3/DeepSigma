#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    outdir = ROOT / "release_kpis"
    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    manual_path = outdir / f"kpi_{version}.json"
    if not manual_path.exists():
        raise SystemExit(f"Missing manual KPI file: {manual_path}")

    manual = json.loads(manual_path.read_text(encoding="utf-8"))
    values = dict(manual.get("values", {}))

    telemetry = json.loads(
        subprocess.check_output(["python", "scripts/kpi_compute.py"], text=True)
    )

    for key, value in telemetry.items():
        if key.startswith("_"):
            continue
        values[key] = float(value)

    merged = {
        "version": version,
        "scale": manual.get("scale", {"min": 0, "max": 10}),
        "values": values,
        "telemetry": telemetry.get("_telemetry", {}),
    }

    merged_path = outdir / f"kpi_{version}_merged.json"
    merged_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote: {merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
