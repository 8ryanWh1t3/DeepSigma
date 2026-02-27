#!/usr/bin/env python3
"""Stale Artifact Kill-Switch — verify release artifacts are fresh and consistent.

Checks:
  1. pyproject.toml version == enterprise/release_kpis/VERSION.txt
  2. Current-version radar PNG exists
  3. badge_latest.svg exists and is recent (<7 days)
  4. history.json contains current version entry
  5. CONTRACT_FINGERPRINT exists and matches schema_manifest.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RK = ROOT / "enterprise" / "release_kpis"


def pyproject_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("Cannot parse version from pyproject.toml")


def check_version_match() -> tuple[bool, str]:
    pv = pyproject_version()
    vt = (RK / "VERSION.txt").read_text(encoding="utf-8").strip().lstrip("v")
    if pv == vt:
        return True, f"version match: {pv}"
    return False, f"version mismatch: pyproject={pv}, VERSION.txt={vt}"


def check_radar_exists() -> tuple[bool, str]:
    version = pyproject_version()
    radar = RK / f"radar_v{version}.png"
    if radar.exists():
        return True, f"radar exists: {radar.name}"
    return False, f"missing radar: {radar.name}"


def check_badge_fresh() -> tuple[bool, str]:
    badge = RK / "badge_latest.svg"
    if not badge.exists():
        return False, "badge_latest.svg missing"
    age_days = (time.time() - badge.stat().st_mtime) / 86400
    if age_days > 7:
        return False, f"badge_latest.svg is {age_days:.1f} days old (max 7)"
    return True, f"badge fresh ({age_days:.1f} days old)"


def check_history_appended() -> tuple[bool, str]:
    version = f"v{pyproject_version()}"
    history = json.loads((RK / "history.json").read_text(encoding="utf-8"))
    versions = [e.get("version") for e in history.get("entries", [])]
    if version in versions:
        return True, f"history contains {version}"
    return False, f"history missing {version} (found: {', '.join(versions)})"


def check_contract_fingerprint() -> tuple[bool, str]:
    fp_path = ROOT / "reference" / "CONTRACT_FINGERPRINT"
    manifest_path = ROOT / "reference" / "schema_manifest.json"
    if not fp_path.exists():
        return False, "reference/CONTRACT_FINGERPRINT missing"
    if not manifest_path.exists():
        return False, "reference/schema_manifest.json missing"
    fp = fp_path.read_text(encoding="utf-8").strip()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_fp = manifest.get("contractFingerprint", "")
    if fp == manifest_fp:
        return True, f"fingerprint match: {fp}"
    return False, f"fingerprint mismatch: file={fp}, manifest={manifest_fp}"


def main() -> int:
    checks = [
        ("version_match", check_version_match),
        ("radar_exists", check_radar_exists),
        ("badge_fresh", check_badge_fresh),
        ("history_appended", check_history_appended),
        ("contract_fingerprint", check_contract_fingerprint),
    ]
    failed = 0
    for name, fn in checks:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not ok:
            failed += 1
    if failed:
        print(f"\nRelease artifact verification FAILED ({failed}/{len(checks)})")
        return 1
    print(f"\nRelease artifact verification PASSED ({len(checks)}/{len(checks)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
