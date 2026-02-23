#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    pack = ROOT / "pilot_pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True, exist_ok=True)

    subprocess.check_call(["make", "issue-label-gate"])
    subprocess.check_call(["make", "kpi-issues"])
    subprocess.check_call(["make", "kpi"])

    outdir = ROOT / "release_kpis"
    version = (outdir / "VERSION.txt").read_text(encoding="utf-8").strip()

    files = [
        outdir / f"radar_{version}.png",
        outdir / f"radar_{version}.svg",
        outdir / "badge_latest.svg",
        outdir / "PR_COMMENT.md",
        outdir / "KPI_GATE_REPORT.md",
        outdir / "ISSUE_LABEL_GATE_REPORT.md",
        outdir / "history.json",
        outdir / "kpi_trend.png",
        outdir / "kpi_trend.svg",
        outdir / "SECURITY_GATE_REPORT.md",
        outdir / "SECURITY_GATE_REPORT.json",
        ROOT / "data" / "security" / "authority_ledger.json",
        ROOT / "artifacts" / "disr_demo" / "authority_ledger.json",
        ROOT / "artifacts" / "disr_demo" / "disr_demo_summary.json",
    ]
    for file_path in files:
        if file_path.exists():
            shutil.copy2(file_path, pack / file_path.name)

    docs = [
        ROOT / "docs" / "docs" / "pilot" / "PILOT_SCOPE.md",
        ROOT / "docs" / "docs" / "pilot" / "DRI_MODEL.md",
        ROOT / "docs" / "docs" / "pilot" / "BRANCH_PROTECTION.md",
        ROOT / "docs" / "docs" / "pilot" / "PILOT_CONTRACT_ONEPAGER.md",
        ROOT / "docs" / "docs" / "release" / "RELEASE_NOTES_v2.0.3.md",
        ROOT / "docs" / "docs" / "governance" / "LABEL_POLICY.md",
        ROOT / "docs" / "docs" / "security" / "DISR.md",
        ROOT / "docs" / "docs" / "security" / "KEY_LIFECYCLE.md",
        ROOT / "docs" / "docs" / "security" / "RECOVERY_RUNBOOK.md",
        ROOT / "docs" / "docs" / "security" / "DEMO_10_MIN.md",
        ROOT / "governance" / "kpi_issue_map.yaml",
        ROOT / "governance" / "kpi_spec.yaml",
    ]
    for doc in docs:
        if doc.exists():
            shutil.copy2(doc, pack / doc.name)

    drills = [
        ROOT / "scripts" / "pilot_in_a_box.py",
        ROOT / "scripts" / "why_60s_challenge.py",
        ROOT / "scripts" / "compute_ci.py",
        ROOT / "scripts" / "reencrypt_demo.py",
    ]
    for drill in drills:
        if drill.exists():
            shutil.copy2(drill, pack / drill.name)

    (pack / "README.md").write_text(
        f"""# Pilot Pack - {version}

This folder is a shareable bundle for pilot evaluation.

## What's inside
- Radar + badge + trend
- KPI gate report + Issue label gate report
- Pilot docs (scope, DRI, branch protection, contract)
- Drill scripts (pilot_in_a_box, why_60s)

## Run locally
```bash
python pilot_in_a_box.py
python why_60s_challenge.py
```
""",
        encoding="utf-8",
    )

    print(f"Built: {pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
