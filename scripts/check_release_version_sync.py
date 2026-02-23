#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
KPI_VERSION = ROOT / "release_kpis" / "VERSION.txt"


def _read_pyproject_version() -> str:
    pattern = re.compile(r'^version\s*=\s*"([^"]+)"\s*$')
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    raise SystemExit(f"Could not locate project version in {PYPROJECT}")


def _read_kpi_version() -> str:
    raw = KPI_VERSION.read_text(encoding="utf-8").strip()
    return raw[1:] if raw.startswith("v") else raw


def main() -> int:
    pyproject_version = _read_pyproject_version()
    kpi_version = _read_kpi_version()
    if pyproject_version != kpi_version:
        raise SystemExit(
            "Version mismatch: "
            f"pyproject.toml={pyproject_version} "
            f"release_kpis/VERSION.txt={kpi_version}"
        )
    print(f"Version sync check passed: {pyproject_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
