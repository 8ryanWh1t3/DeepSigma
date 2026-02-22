#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

KPI_PREFIX = "kpi:"
SEV_PREFIX = "sev:"
TYPE_PREFIX = "type:"

ALLOWED_SEV = {"sev:P0", "sev:P1", "sev:P2", "sev:P3"}
ALLOWED_TYPE = {"type:feature", "type:bug", "type:debt", "type:doc"}


def run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def gh_list_issues(state: str) -> List[Dict]:
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--state",
            state,
            "--limit",
            "500",
            "--json",
            "number,title,labels,url",
        ]
    )
    return json.loads(out) if out else []


def extract(labels: List[Dict[str, str]]) -> Tuple[List[str], List[str], List[str]]:
    names = [label["name"] for label in labels]
    kpis = [label for label in names if label.startswith(KPI_PREFIX)]
    sevs = [label for label in names if label.startswith(SEV_PREFIX)]
    types = [label for label in names if label.startswith(TYPE_PREFIX)]
    return kpis, sevs, types


def validate_issue(issue: Dict) -> List[str]:
    errors: List[str] = []
    kpis, sevs, types = extract(issue.get("labels", []))

    if len(kpis) != 1:
        errors.append(f"KPI labels: expected 1, got {len(kpis)} ({kpis})")
    if len(sevs) != 1:
        errors.append(f"Severity labels: expected 1, got {len(sevs)} ({sevs})")
    elif sevs[0] not in ALLOWED_SEV:
        errors.append(f"Severity label not allowed: {sevs[0]}")
    if len(types) != 1:
        errors.append(f"Type labels: expected 1, got {len(types)} ({types})")
    elif types[0] not in ALLOWED_TYPE:
        errors.append(f"Type label not allowed: {types[0]}")

    return errors


def main() -> int:
    enforce_all = os.environ.get("ENFORCE_ALL_ISSUES", "0") == "1"
    open_issues = gh_list_issues("open")
    failures = []

    for issue in open_issues:
        kpis, _, _ = extract(issue.get("labels", []))
        participates = bool(kpis) or enforce_all
        if not participates:
            continue

        errors = validate_issue(issue)
        if errors:
            failures.append(
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "url": issue["url"],
                    "errors": errors,
                }
            )

    outdir = ROOT / "release_kpis"
    outdir.mkdir(parents=True, exist_ok=True)
    report = outdir / "ISSUE_LABEL_GATE_REPORT.md"

    lines = ["# Issue Label Gate Report", ""]
    if failures:
        lines.extend(["## FAIL", ""])
        for failure in failures:
            lines.append(f"- #{failure['number']}: {failure['title']}")
            lines.append(f"  - {failure['url']}")
            for error in failure["errors"]:
                lines.append(f"  - {error}")
            lines.append("")
    else:
        lines.extend(
            [
                "## PASS",
                "",
                "- All KPI-participating issues have exactly 1 KPI + 1 severity + 1 type label.",
                "",
            ]
        )

    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {report}")

    if failures:
        raise SystemExit("Issue label gate FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
