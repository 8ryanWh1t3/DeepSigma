#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def parse_scalar(raw: str):
    value = raw.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("{") and value.endswith("}"):
        body = value[1:-1].strip()
        result: dict[str, float | int | str] = {}
        if not body:
            return result
        for part in body.split(","):
            key, item = part.split(":", 1)
            k = key.strip()
            v = item.strip()
            if "." in v:
                try:
                    result[k] = float(v)
                    continue
                except ValueError:
                    pass
            try:
                result[k] = int(v)
                continue
            except ValueError:
                result[k] = v.strip('"').strip("'")
        return result
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass
    try:
        return int(value)
    except ValueError:
        return value


def load_yaml_like(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        key, value = stripped.split(":", 1)
        k = key.strip()
        v = value.strip()
        if not v:
            node: dict = {}
            parent[k] = node
            stack.append((indent, node))
        else:
            parent[k] = parse_scalar(v)
    return root


def iso_to_date(raw: str) -> dt.date:
    return dt.date.fromisoformat(raw[:10])


def today() -> dt.date:
    return dt.date.today()


def gh_issues(label: str, state: str) -> list[dict]:
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--label",
            label,
            "--state",
            state,
            "--limit",
            "500",
            "--json",
            "number,title,labels,createdAt,closedAt",
        ]
    )
    return json.loads(out) if out else []


def get_severity(issue: dict) -> str:
    labels = {item["name"] for item in issue.get("labels", [])}
    for sev in ("P0", "P1", "P2", "P3"):
        if f"sev:{sev}" in labels:
            return sev
    return "P2"


def get_type(issue: dict) -> str:
    labels = {item["name"] for item in issue.get("labels", [])}
    for kind in ("feature", "bug", "debt", "doc"):
        if f"type:{kind}" in labels:
            return kind
    return "feature"


def weight(issue: dict, severity_map: dict, type_weights: dict) -> float:
    sev = get_severity(issue)
    kind = get_type(issue)
    return float(severity_map[sev]["credit"]) * float(type_weights[kind])


def overdue(issue: dict, severity_map: dict) -> bool:
    sev = get_severity(issue)
    sla_days = int(severity_map[sev]["sla_days"])
    created = iso_to_date(issue["createdAt"])
    return (today() - created).days > sla_days


def any_open_p0(issues: list[dict]) -> bool:
    return any(get_severity(issue) == "P0" for issue in issues)


def main() -> int:
    mapping = load_yaml_like(ROOT / "governance/kpi_issue_map.yaml")
    severity_map = mapping["severity"]
    type_weights = mapping["type_weight"]
    scoring = mapping["scoring"]
    kpis = mapping["kpis"]

    since = today() - dt.timedelta(days=30)
    result: dict[str, object] = {"since": since.isoformat(), "kpis": {}}

    for key, meta in kpis.items():
        label = meta["label"]
        open_issues = gh_issues(label, "open")
        closed_issues = gh_issues(label, "closed")
        closed_since = [
            issue
            for issue in closed_issues
            if issue.get("closedAt") and iso_to_date(issue["closedAt"]) >= since
        ]

        credit = sum(weight(issue, severity_map, type_weights) for issue in closed_since)
        debt = sum(
            weight(issue, severity_map, type_weights)
            for issue in open_issues
            if overdue(issue, severity_map)
        )

        cap = float(scoring["p0_open_cap"]) if any_open_p0(open_issues) else None
        result["kpis"][key] = {
            "label": label,
            "open_count": len(open_issues),
            "closed_since_count": len(closed_since),
            "credit_delta": round(credit * float(scoring["close_credit_points"]), 2),
            "debt_delta": round(debt * float(scoring["overdue_debt_points"]), 2),
            "cap_if_open_p0": cap,
        }

    out = ROOT / "release_kpis" / "issue_deltas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
