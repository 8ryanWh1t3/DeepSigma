#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = ROOT / "pilot"
REPORT_JSON = PILOT_DIR / "reports" / "ci_report.json"
REPORT_MD = PILOT_DIR / "reports" / "ci_report.md"

ID_RE = re.compile(r"\b(?:A-\d{4}-\d{3}|DRIFT-\d{4}-\d{3}|PATCH-\d{4}-\d{3}|DLR-\d{4}-\d{3})\b")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class Violation:
    category: str
    file: str
    message: str
    issue_ref: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {
            "category": self.category,
            "file": self.file,
            "message": self.message,
        }
        if self.issue_ref:
            payload["issue_ref"] = self.issue_ref
        return payload


@dataclass
class AssumptionRecord:
    path: Path
    assumption_id: str
    expiry: date | None


@dataclass
class DriftRecord:
    path: Path
    drift_id: str
    status: str


@dataclass
class DecisionRecord:
    path: Path
    decision_id: str
    owner: str
    seal: str
    linked_assumptions: list[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_field(text: str, field: str) -> str:
    pattern = re.compile(rf"^\s*[-*]?\s*{re.escape(field)}\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def extract_date(value: str) -> date | None:
    if not value:
        return None
    match = DATE_RE.search(value)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def list_markdown(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.glob("*.md"))


def collect_assumptions(paths: Iterable[Path]) -> list[AssumptionRecord]:
    results: list[AssumptionRecord] = []
    for path in paths:
        text = read_text(path)
        assumption_id = extract_field(text, "Assumption ID") or path.stem
        expiry = extract_date(extract_field(text, "Expiry date (YYYY-MM-DD)"))
        results.append(AssumptionRecord(path=path, assumption_id=assumption_id, expiry=expiry))
    return results


def collect_drifts(paths: Iterable[Path]) -> list[DriftRecord]:
    results: list[DriftRecord] = []
    for path in paths:
        text = read_text(path)
        drift_id = extract_field(text, "Drift ID") or path.stem
        status = extract_field(text, "Status") or "Open"
        results.append(DriftRecord(path=path, drift_id=drift_id, status=status))
    return results


def collect_decisions(paths: Iterable[Path]) -> list[DecisionRecord]:
    results: list[DecisionRecord] = []
    for path in paths:
        text = read_text(path)
        decision_id = extract_field(text, "Decision ID")
        if not decision_id:
            ids = [token for token in ID_RE.findall(text) if token.startswith("DLR-")]
            decision_id = ids[0] if ids else path.stem
        owner = extract_field(text, "Owner")
        seal = extract_field(text, "Seal")
        linked_assumptions = sorted(set(token for token in ID_RE.findall(text) if token.startswith("A-")))
        results.append(
            DecisionRecord(
                path=path,
                decision_id=decision_id,
                owner=owner,
                seal=seal,
                linked_assumptions=linked_assumptions,
            )
        )
    return results


def main() -> int:
    today = date.today()
    timestamp = datetime.now(timezone.utc).isoformat()

    decisions = collect_decisions(list_markdown(PILOT_DIR / "decisions"))
    assumptions = collect_assumptions(list_markdown(PILOT_DIR / "assumptions"))
    drifts = collect_drifts(list_markdown(PILOT_DIR / "drift"))
    patch_paths = list_markdown(PILOT_DIR / "patches")
    patch_texts = {path: read_text(path) for path in patch_paths}

    patched_assumptions: set[str] = set()
    linked_drifts_in_patches: set[str] = set()
    for path, text in patch_texts.items():
        _ = path
        for token in ID_RE.findall(text):
            if token.startswith("A-"):
                patched_assumptions.add(token)
            if token.startswith("DRIFT-"):
                linked_drifts_in_patches.add(token)

    violations: list[Violation] = []
    ci = 100

    expired_unpatched = 0
    for assumption in assumptions:
        if assumption.expiry and assumption.expiry < today and assumption.assumption_id not in patched_assumptions:
            expired_unpatched += 1
            ci -= 20
            violations.append(
                Violation(
                    category="expired_assumption",
                    file=str(assumption.path.relative_to(ROOT)),
                    message=f"{assumption.assumption_id} expired on {assumption.expiry.isoformat()} and has no linked patch",
                )
            )

    open_drifts = 0
    for drift in drifts:
        if drift.status.strip().lower() not in {"closed", "resolved", "patched"}:
            open_drifts += 1
            ci -= 10
            violations.append(
                Violation(
                    category="open_drift",
                    file=str(drift.path.relative_to(ROOT)),
                    message=f"{drift.drift_id} is open and still contributes to drift risk",
                    issue_ref=drift.drift_id,
                )
            )

    for decision in decisions:
        rel = str(decision.path.relative_to(ROOT))
        if not decision.owner:
            ci -= 5
            violations.append(
                Violation(
                    category="missing_owner",
                    file=rel,
                    message=f"{decision.decision_id} is missing Owner",
                )
            )
        seal_value = decision.seal.strip().lower()
        if not seal_value or "placeholder" in seal_value or seal_value in {"none", "tbd", "na"}:
            ci -= 5
            violations.append(
                Violation(
                    category="missing_seal",
                    file=rel,
                    message=f"{decision.decision_id} is missing Seal",
                )
            )
        if not decision.linked_assumptions:
            ci -= 5
            violations.append(
                Violation(
                    category="missing_assumptions",
                    file=rel,
                    message=f"{decision.decision_id} has no linked assumptions",
                )
            )

    drift_without_patch = 0
    for drift in drifts:
        if drift.drift_id not in linked_drifts_in_patches:
            drift_without_patch += 1
            ci -= 5
            violations.append(
                Violation(
                    category="drift_without_patch",
                    file=str(drift.path.relative_to(ROOT)),
                    message=f"{drift.drift_id} has no linked patch",
                    issue_ref=drift.drift_id,
                )
            )

    ci = max(ci, 0)

    report = {
        "timestamp": timestamp,
        "ci_score": ci,
        "counts": {
            "decisions": len(decisions),
            "assumptions": len(assumptions),
            "expired_assumptions": sum(1 for a in assumptions if a.expiry and a.expiry < today),
            "expired_assumptions_unpatched": expired_unpatched,
            "drift": len(drifts),
            "drift_open": open_drifts,
            "patches": len(patch_paths),
        },
        "violations": [v.as_dict() for v in violations],
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Coherence Index Report",
        "",
        f"- Timestamp (UTC): {timestamp}",
        f"- CI score: **{ci}**",
        "",
        "## Counts",
        "",
        f"- Decisions: {report['counts']['decisions']}",
        f"- Assumptions: {report['counts']['assumptions']}",
        f"- Expired assumptions: {report['counts']['expired_assumptions']}",
        f"- Expired assumptions (unpatched): {report['counts']['expired_assumptions_unpatched']}",
        f"- Drift records: {report['counts']['drift']}",
        f"- Open drift records: {report['counts']['drift_open']}",
        f"- Patch records: {report['counts']['patches']}",
        "",
        "## Violations",
        "",
    ]

    if violations:
        for violation in violations:
            issue_piece = f" ({violation.issue_ref})" if violation.issue_ref else ""
            lines.append(f"- `{violation.file}`: {violation.message}{issue_piece}")
    else:
        lines.append("- None")

    lines.extend(["", "## Gate", ""])
    if ci < 75:
        lines.append("- Status: FAIL (CI < 75)")
    elif ci < 90:
        lines.append("- Status: WARN (75 <= CI < 90)")
    else:
        lines.append("- Status: PASS (CI >= 90)")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"CI score: {ci}")
    print(f"Report JSON: {REPORT_JSON.relative_to(ROOT)}")
    print(f"Report MD: {REPORT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
