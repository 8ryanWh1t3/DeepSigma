#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def main() -> int:
    outdir = ROOT / "release_kpis"
    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()
    merged_path = outdir / f"kpi_{version}_merged.json"
    merged = json.loads(merged_path.read_text(encoding="utf-8"))

    eligibility = merged.get("eligibility", {}).get("kpis", {})
    values = merged.get("values", {})

    confidence: dict[str, float] = {}
    bands: dict[str, dict[str, float]] = {}

    for kpi, value in values.items():
        kpi_elig = eligibility.get(kpi, {})
        c = float(kpi_elig.get("confidence", 0.35))
        c = clamp(c, 0.20, 0.95)
        half_width = (1.0 - c) * 2.5
        low = clamp(float(value) - half_width, 0.0, 10.0)
        high = clamp(float(value) + half_width, 0.0, 10.0)
        confidence[kpi] = round(c, 3)
        bands[kpi] = {"low": round(low, 2), "high": round(high, 2)}

    confidence_payload = {
        "schema": "kpi_confidence_v1",
        "version": version,
        "confidence": confidence,
        "source": "eligibility-tier-capped",
    }
    bands_payload = {
        "schema": "kpi_bands_v1",
        "version": version,
        "bands": bands,
        "formula": "half_width=(1-confidence)*2.5",
    }

    (outdir / "kpi_confidence.json").write_text(
        json.dumps(confidence_payload, indent=2) + "\n", encoding="utf-8"
    )
    (outdir / f"kpi_bands_{version}.json").write_text(
        json.dumps(bands_payload, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote: {outdir / 'kpi_confidence.json'}")
    print(f"Wrote: {outdir / f'kpi_bands_{version}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
