#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_ROOT = ENT_ROOT / "release_kpis" / "health"
HISTORY_ROOT = HEALTH_ROOT / "history"

ICR_POINTS = {
    "ICR-1": 1,
    "ICR-2": 2,
    "ICR-3": 3,
    "ICR-4": 5,
    "ICR-5": 8,
}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def parse_icr_label(labels: list[str]) -> str | None:
    for raw in labels:
        normalized = raw.strip().upper()
        if normalized in ICR_POINTS:
            return normalized
    return None


def load_issues(from_gh: bool) -> list[dict[str, Any]]:
    if from_gh:
        payload = run(
            [
                "gh",
                "issue",
                "list",
                "--state",
                "all",
                "--limit",
                "500",
                "--json",
                "number,title,labels,state,createdAt,updatedAt,closedAt",
            ]
        )
        return json.loads(payload) if payload else []

    local = ENT_ROOT / "release_kpis" / "issues_all.json"
    if local.exists():
        payload = json.loads(local.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
    return []


def issue_labels(issue: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for label in issue.get("labels", []):
        if isinstance(label, str):
            out.append(label)
        elif isinstance(label, dict):
            name = label.get("name")
            if isinstance(name, str):
                out.append(name)
    return out


def age_days(issue: dict[str, Any], now: dt.datetime) -> int:
    created_at = issue.get("createdAt")
    if not isinstance(created_at, str):
        return 0
    created = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return max((now - created).days, 0)


def summarize(issues: list[dict[str, Any]]) -> dict[str, Any]:
    now = dt.datetime.now(dt.UTC)
    open_issues = [i for i in issues if str(i.get("state", "")).upper() == "OPEN"]

    unlabeled = 0
    rl_open = 0
    icr5_oldest = 0
    ages: list[int] = []
    high_risk_count = 0
    by_band = {"ICR-1": 0, "ICR-2": 0, "ICR-3": 0, "ICR-4": 0, "ICR-5": 0}

    for issue in open_issues:
        labels = issue_labels(issue)
        band = parse_icr_label(labels)
        if band is None:
            band = "ICR-3"
            unlabeled += 1
        points = ICR_POINTS[band]
        rl_open += points
        by_band[band] += 1
        issue_age = age_days(issue, now)
        ages.append(issue_age)
        if band in {"ICR-4", "ICR-5"}:
            high_risk_count += 1
        if band == "ICR-5":
            icr5_oldest = max(icr5_oldest, issue_age)

    high_share = (high_risk_count / len(open_issues)) if open_issues else 0.0
    median_age_45 = sum(1 for n in ages if n >= 45)
    if rl_open >= 400 or high_share >= 0.2 or icr5_oldest >= 30:
        status = "RED"
    elif rl_open >= 150 or high_share >= 0.08 or median_age_45 > 0:
        status = "YELLOW"
    else:
        status = "GREEN"

    return {
        "schema": "icr_health_v2",
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window": "all_open",
        "status": status,
        "metrics": {
            "issues_open": len(open_issues),
            "rl_open": rl_open,
            "high_share": round(high_share, 4),
            "median_age_45_count": median_age_45,
            "icr5_oldest_days": icr5_oldest,
            "unlabeled_fallback_count": unlabeled,
        },
        "bands_open": by_band,
    }


def write_outputs(payload: dict[str, Any], snapshot: bool) -> None:
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)

    latest_json = HEALTH_ROOT / "icr_latest.json"
    latest_md = HEALTH_ROOT / "icr_latest.md"
    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ICR Health (Latest)",
        "",
        f"- Status: **{payload['status']}**",
        f"- RL_open: **{payload['metrics']['rl_open']}**",
        f"- high_share: **{payload['metrics']['high_share']}**",
        f"- median_age_45_count: **{payload['metrics']['median_age_45_count']}**",
        f"- icr5_oldest_days: **{payload['metrics']['icr5_oldest_days']}**",
        f"- unlabeled_fallback_count: **{payload['metrics']['unlabeled_fallback_count']}**",
        "",
        "## Open by Band",
    ]
    for band, count in payload["bands_open"].items():
        lines.append(f"- {band}: **{count}**")
    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if snapshot:
        stamp = dt.date.today().isoformat()
        (HISTORY_ROOT / f"ICR_SNAPSHOT_{stamp}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-gh", action="store_true", help="Load issues from GitHub CLI instead of local snapshot.")
    parser.add_argument("--snapshot", action="store_true", help="Write daily dated snapshot JSON.")
    args = parser.parse_args()

    issues = load_issues(from_gh=args.from_gh)
    payload = summarize(issues)
    write_outputs(payload, snapshot=args.snapshot)
    print(f"Wrote: {HEALTH_ROOT / 'icr_latest.json'}")
    print(f"Wrote: {HEALTH_ROOT / 'icr_latest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
