#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "release_kpis"
OPEN_JSON = OUTDIR / "issues_open.json"

KPI_KEYS = [
    "technical_completeness",
    "automation_depth",
    "authority_modeling",
    "enterprise_readiness",
    "scalability",
    "data_integration",
    "economic_measurability",
    "operational_maturity",
]


def labels(issue: dict) -> list[str]:
    return [label["name"] for label in issue.get("labels", [])]


def age_days(created_at: str) -> int:
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return int((now - dt).days)


def pick_one(prefix: str, labs: list[str]) -> str:
    xs = [label for label in labs if label.startswith(prefix)]
    return xs[0] if xs else ""


def main() -> int:
    if not OPEN_JSON.exists():
        raise SystemExit("Missing release_kpis/issues_open.json. Export issues first.")

    issues = json.loads(OPEN_JSON.read_text(encoding="utf-8"))

    portfolio = {
        k: {"open": 0, "p0": 0, "p1": 0, "over30": 0, "top": []} for k in KPI_KEYS
    }
    kill = []

    for it in issues:
        labs = labels(it)
        kpi = pick_one("kpi:", labs).replace("kpi:", "")
        sev = pick_one("sev:", labs)
        typ = pick_one("type:", labs)
        created = it.get("createdAt") or ""
        age = age_days(created) if created else 0

        if sev in ("sev:P0", "sev:P1"):
            kill.append((sev, it["number"], it["title"], it["url"], age, kpi, typ))

        if kpi in portfolio:
            p = portfolio[kpi]
            p["open"] += 1
            if sev == "sev:P0":
                p["p0"] += 1
            if sev == "sev:P1":
                p["p1"] += 1
            if age >= 30:
                p["over30"] += 1
            p["top"].append((age, it["number"], it["title"], it["url"], sev, typ))

    for k in KPI_KEYS:
        portfolio[k]["top"].sort(reverse=True, key=lambda x: x[0])
        portfolio[k]["top"] = portfolio[k]["top"][:5]

    csv_path = OUTDIR / "issues_kpi_matrix.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kpi", "open", "p0", "p1", "over30"])
        for k in KPI_KEYS:
            p = portfolio[k]
            w.writerow([k, p["open"], p["p0"], p["p1"], p["over30"]])

    kill.sort(key=lambda x: (x[0], -x[4]))
    kill_path = OUTDIR / "issues_kill_list.md"
    lines = ["# Kill List (Open sev:P0 / sev:P1)", ""]
    if not kill:
        lines += ["- None ✅", ""]
    else:
        for sev, num, title, url, age, kpi, typ in kill:
            lines.append(f"- **{sev}** #{num} ({age}d) — {title}")
            lines.append(f"  - {url}")
            if kpi:
                lines.append(f"  - KPI: `{kpi}`")
            if typ:
                lines.append(f"  - Type: `{typ}`")
            lines.append("")
    kill_path.write_text("\n".join(lines), encoding="utf-8")

    brief_path = OUTDIR / "issues_portfolio_summary.md"
    b = ["# KPI Portfolio Summary (Open Issues)", ""]
    for k in KPI_KEYS:
        p = portfolio[k]
        b.append(f"## {k}")
        b.append(
            f"- Open: **{p['open']}** | P0: **{p['p0']}** | P1: **{p['p1']}** | Age≥30d: **{p['over30']}**"
        )
        b.append("")
        if p["top"]:
            b.append("Top oldest (moves radar fastest if closed):")
            for age, num, title, url, sev, typ in p["top"]:
                b.append(f"- ({age}d) **{sev or 'sev:?'}** #{num} [{typ or 'type:?'}] — {title}")
                b.append(f"  - {url}")
            b.append("")
        else:
            b.append("- None")
            b.append("")
    brief_path.write_text("\n".join(b), encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {kill_path}")
    print(f"Wrote: {brief_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
