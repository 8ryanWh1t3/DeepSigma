#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "roadmap" / "roadmap.json"
README_PATH = ROOT / "README.md"
OUTDIR = ROOT / "release_kpis"


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def normalize_versions(roadmap: dict) -> tuple[str | None, set[str]]:
    active = None
    dormant: set[str] = set()
    for version, payload in roadmap.items():
        status = str(payload.get("status", "")).lower()
        if status == "active":
            if active is not None:
                raise SystemExit("Multiple active roadmap versions found")
            active = version
        if status == "dormant":
            dormant.add(version)
    return active, dormant


def check_readme(active: str, dormant: set[str]) -> list[str]:
    failures: list[str] = []
    text = README_PATH.read_text(encoding="utf-8")
    if active not in text:
        failures.append(f"README missing active roadmap version marker: {active}")
    for version in sorted(dormant):
        if version not in text:
            failures.append(f"README missing dormant roadmap version marker: {version}")
    if "Future Track" not in text:
        failures.append("README missing 'Future Track' section")
    return failures


def check_issue_scope(active: str | None, dormant: set[str]) -> list[str]:
    failures: list[str] = []
    if not os.getenv("GH_TOKEN") and not os.getenv("GITHUB_TOKEN"):
        return failures

    try:
        repo = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    except Exception:
        return failures

    def fetch(label: str) -> list[dict]:
        out = run([
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--label",
            label,
            "--limit",
            "200",
            "--json",
            "number,title,labels,url",
        ])
        return json.loads(out) if out else []

    # Dormant tracks must keep 'dormant' label.
    for version in dormant:
        for issue in fetch(version):
            labels = {entry["name"] for entry in issue.get("labels", [])}
            if "dormant" not in labels:
                failures.append(f"{version} issue #{issue['number']} missing 'dormant' label")

    # Active track must not include dormant label.
    if active:
        for issue in fetch(active):
            labels = {entry["name"] for entry in issue.get("labels", [])}
            if "dormant" in labels:
                failures.append(f"{active} issue #{issue['number']} incorrectly labeled 'dormant'")

    return failures


def main() -> int:
    if not ROADMAP_PATH.exists():
        raise SystemExit(f"Missing roadmap file: {ROADMAP_PATH}")

    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    active, dormant = normalize_versions(roadmap)
    if not active:
        raise SystemExit("No active roadmap version found")

    failures: list[str] = []
    failures.extend(check_readme(active, dormant))
    failures.extend(check_issue_scope(active, dormant))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    report = OUTDIR / "ROADMAP_SCOPE_GATE_REPORT.md"
    lines = ["# Roadmap Scope Gate Report", "", f"Active version: `{active}`", ""]

    if failures:
        lines.append("## FAIL")
        lines.append("")
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("## PASS")
        lines.append("")
        lines.append("- Roadmap active/dormant contract is valid")
        lines.append("- README references active + future tracks")
        lines.append("- Issue labels (if GH token available) satisfy scope discipline")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {report}")

    if failures:
        raise SystemExit("Roadmap scope gate FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
