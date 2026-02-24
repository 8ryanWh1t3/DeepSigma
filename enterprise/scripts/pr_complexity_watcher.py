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

PCR_POINTS = {"PCR-1": 1, "PCR-2": 2, "PCR-3": 3, "PCR-4": 5, "PCR-5": 8}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def parse_version_date(raw: str | None) -> dt.datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_prs(from_gh: bool) -> list[dict[str, Any]]:
    if from_gh:
        payload = run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "300",
                "--json",
                "number,title,body,additions,deletions,changedFiles,mergedAt,baseRefName,headRefName",
            ]
        )
        return json.loads(payload) if payload else []
    local = ENT_ROOT / "release_kpis" / "prs_merged.json"
    if local.exists():
        payload = json.loads(local.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
    return []


def classify_pcr(score: float) -> str:
    if score < 3:
        return "PCR-1"
    if score < 6:
        return "PCR-2"
    if score < 10:
        return "PCR-3"
    if score < 15:
        return "PCR-4"
    return "PCR-5"


def pr_score(pr: dict[str, Any]) -> tuple[float, dict[str, float]]:
    files = float(pr.get("changedFiles", 0) or 0)
    additions = float(pr.get("additions", 0) or 0)
    deletions = float(pr.get("deletions", 0) or 0)
    churn = additions + deletions
    title = str(pr.get("title", "")).lower()
    body = str(pr.get("body", "")).lower()
    text = f"{title}\n{body}"

    risky = 0.0
    risky += 2.0 if "security" in text else 0.0
    risky += 1.5 if "workflow" in text or ".github/workflows" in text else 0.0
    risky += 1.5 if "schema" in text else 0.0
    boundary = 0.0
    boundary += 1.5 if "core" in text and "enterprise" in text else 0.0
    test_delta = 0.5 if "test" in text else 0.0

    score = (files * 0.35) + (churn / 250.0) + risky + boundary + test_delta
    details = {
        "files_component": round(files * 0.35, 3),
        "churn_component": round(churn / 250.0, 3),
        "risky_component": round(risky, 3),
        "boundary_component": round(boundary, 3),
        "test_component": round(test_delta, 3),
    }
    return score, details


def cl14_bucket(points: int, thresholds: dict[str, int]) -> str:
    if points <= thresholds["low_max"]:
        return "low"
    if points <= thresholds["medium_max"]:
        return "medium"
    if points <= thresholds["high_max"]:
        return "high"
    return "extreme"


def load_thresholds() -> dict[str, int]:
    policy = ENT_ROOT / "governance" / "tec_ctec_policy.json"
    data = json.loads(policy.read_text(encoding="utf-8"))
    thresholds = data.get("ccf_thresholds", {})
    return {
        "low_max": int(thresholds.get("low_max", 25)),
        "medium_max": int(thresholds.get("medium_max", 60)),
        "high_max": int(thresholds.get("high_max", 120)),
    }


def summarize(prs: list[dict[str, Any]]) -> dict[str, Any]:
    now = dt.datetime.now(dt.UTC)
    window_start = now - dt.timedelta(days=14)
    recent = []
    bucket_counts = {"PCR-1": 0, "PCR-2": 0, "PCR-3": 0, "PCR-4": 0, "PCR-5": 0}
    cl14 = 0
    records = []

    for pr in prs:
        merged_at = parse_version_date(pr.get("mergedAt"))
        score, details = pr_score(pr)
        pcr = classify_pcr(score)
        bucket_counts[pcr] += 1
        record = {
            "number": pr.get("number"),
            "mergedAt": pr.get("mergedAt"),
            "score": round(score, 3),
            "pcr": pcr,
            "points": PCR_POINTS[pcr],
            "details": details,
        }
        records.append(record)

        if merged_at and merged_at >= window_start:
            recent.append(record)
            cl14 += PCR_POINTS[pcr]

    thresholds = load_thresholds()
    load_bucket = cl14_bucket(cl14, thresholds)
    return {
        "schema": "pcr_health_v2",
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window_days": 14,
        "cl14": cl14,
        "load_bucket": load_bucket,
        "counts": {
            "prs_total": len(prs),
            "prs_14d": len(recent),
            "by_pcr": bucket_counts,
        },
        "recent_14d": recent,
        "provisional_thresholds": True,
    }


def maybe_label_prs(payload: dict[str, Any], enable: bool) -> None:
    if not enable:
        return
    recent = payload.get("recent_14d", [])
    for row in recent:
        number = row.get("number")
        pcr = row.get("pcr")
        if not isinstance(number, int) or not isinstance(pcr, str):
            continue
        run(["gh", "pr", "edit", str(number), "--add-label", pcr])


def write_outputs(payload: dict[str, Any], snapshot: bool) -> None:
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)

    latest_json = HEALTH_ROOT / "pcr_latest.json"
    latest_md = HEALTH_ROOT / "pcr_latest.md"
    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# PCR Health (Latest)",
        "",
        f"- CL14: **{payload['cl14']}**",
        f"- Load bucket: **{payload['load_bucket']}**",
        f"- PRs in last 14 days: **{payload['counts']['prs_14d']}**",
        "",
        "## PCR distribution",
    ]
    for key, count in payload["counts"]["by_pcr"].items():
        lines.append(f"- {key}: **{count}**")
    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if snapshot:
        stamp = dt.date.today().isoformat()
        (HISTORY_ROOT / f"PCR_SNAPSHOT_{stamp}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-gh", action="store_true", help="Load merged PRs from GitHub CLI instead of local snapshot.")
    parser.add_argument("--label-prs", action="store_true", help="Apply PCR labels to recent PRs.")
    parser.add_argument("--snapshot", action="store_true", help="Write daily dated snapshot JSON.")
    args = parser.parse_args()

    prs = load_prs(from_gh=args.from_gh)
    payload = summarize(prs)
    maybe_label_prs(payload, enable=args.label_prs)
    write_outputs(payload, snapshot=args.snapshot)
    print(f"Wrote: {HEALTH_ROOT / 'pcr_latest.json'}")
    print(f"Wrote: {HEALTH_ROOT / 'pcr_latest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
