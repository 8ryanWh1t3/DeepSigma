#!/usr/bin/env python3
"""Generate a validated MDPT Prompt Index from a PromptCapabilities CSV export.

Usage:
    python mdpt/tools/generate_prompt_index.py --csv <file.csv> --out <dir>
    python mdpt/tools/generate_prompt_index.py --csv <file.csv> --out <dir> --include-nonapproved

Reads a CSV exported from the PromptCapabilities SharePoint list,
filters to Approved rows by default, validates required fields,
normalises values, sorts deterministically, and emits:
  - prompt_index.json          (machine-readable, schema-validated)
  - prompt_index_summary.md    (human-readable rollup)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_MDPT_ROOT = _THIS_DIR.parent
_REPO_ROOT = _MDPT_ROOT.parent

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA_PATH = _MDPT_ROOT / "templates" / "prompt_index_schema.json"

# ── Required CSV columns ────────────────────────────────────────────────
REQUIRED_FIELDS = [
    "CapabilityID",
    "Title",
    "Status",
    "RiskLane",
    "TTL_Hours",
    "LatestVersion",
    "LatestApprovedDate",
    "LatestPromptMatrixLink",
    "ExamplesLink",
    "ManifestLink",
]

VALID_RISK_LANES = {"GREEN", "YELLOW", "RED"}

# ── Date parsing helpers ────────────────────────────────────────────────
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y",
]


def _parse_date(raw: str) -> str | None:
    """Parse a date string leniently and return ISO 8601, or None."""
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return raw  # keep original if nothing matches


def _to_int(raw: str) -> int | None:
    raw = raw.strip()
    if not raw:
        return None
    return int(float(raw))


def _to_float(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


def _split_tags(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    for sep in [";", ","]:
        if sep in raw:
            return [t.strip() for t in raw.split(sep) if t.strip()]
    return [raw]


# ── Core pipeline functions ─────────────────────────────────────────────

def load_csv(csv_path: str) -> list[dict[str, str]]:
    """Read CSV via stdlib csv.DictReader. Returns list of row dicts."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def filter_approved(
    rows: list[dict[str, str]],
    include_nonapproved: bool = False,
) -> list[dict[str, str]]:
    """Return only Approved rows unless include_nonapproved is True."""
    if include_nonapproved:
        return list(rows)
    return [r for r in rows if r.get("Status", "").strip().lower() == "approved"]


def validate_required(row: dict[str, str], row_index: int) -> list[str]:
    """Validate required fields on a single row. Returns error strings."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        val = row.get(field, "").strip()
        if not val:
            errors.append(f"Row {row_index}: missing required field '{field}'")
    lane = row.get("RiskLane", "").strip().upper()
    if lane and lane not in VALID_RISK_LANES:
        errors.append(
            f"Row {row_index}: invalid RiskLane '{lane}', "
            f"expected one of {sorted(VALID_RISK_LANES)}"
        )
    return errors


def normalize_row(row: dict[str, str]) -> dict:
    """Convert a flat CSV row dict into the nested JSON capability object."""
    return {
        "capability_id": row.get("CapabilityID", "").strip(),
        "title": row.get("Title", "").strip(),
        "description": row.get("Description", "").strip(),
        "owner_dri": row.get("OwnerDRI", "").strip(),
        "approver": row.get("Approver", "").strip(),
        "team": row.get("Team", "").strip(),
        "use_case": row.get("UseCase", "").strip(),
        "audience": row.get("Audience", "").strip(),
        "tags": _split_tags(row.get("Tags", "")),
        "risk_lane": row.get("RiskLane", "").strip().upper(),
        "ttl_hours": _to_float(row.get("TTL_Hours", "")) or 0,
        "review_cadence_days": _to_int(row.get("ReviewCadenceDays", "")),
        "status": row.get("Status", "").strip().title(),
        "latest_version": row.get("LatestVersion", "").strip(),
        "latest_approved_date": _parse_date(row.get("LatestApprovedDate", "")),
        "links": {
            "prompt_matrix": row.get("LatestPromptMatrixLink", "").strip(),
            "examples": row.get("ExamplesLink", "").strip(),
            "manifest": row.get("ManifestLink", "").strip(),
        },
        "telemetry": {
            "last_eval_score": _to_float(row.get("LastEvalScore", "")),
            "run_count": _to_int(row.get("RunCount", "")),
            "drift_count": _to_int(row.get("DriftCount", "")),
            "patch_count": _to_int(row.get("PatchCount", "")),
            "last_drift_date": _parse_date(row.get("LastDriftDate", "")),
        },
    }


def sort_capabilities(caps: list[dict]) -> list[dict]:
    """Deterministic sort: capability_id asc, then latest_version asc."""
    return sorted(caps, key=lambda c: (c["capability_id"], c["latest_version"]))


def build_counts(caps: list[dict]) -> dict:
    """Compute rollup counts."""
    lane_counts = Counter(c["risk_lane"] for c in caps)
    use_counts = Counter(c["use_case"] for c in caps if c["use_case"])
    top_use = use_counts.most_common(5)
    return {
        "total": len(caps),
        "by_risk_lane": dict(sorted(lane_counts.items())),
        "by_use_case": [
            {"use_case": uc, "count": cnt} for uc, cnt in top_use
        ],
    }


def build_index(
    csv_path: str,
    include_nonapproved: bool = False,
) -> tuple[dict, list[str]]:
    """Build the full prompt index dict. Returns (index_dict, errors)."""
    all_rows = load_csv(csv_path)
    filtered = filter_approved(all_rows, include_nonapproved)

    errors: list[str] = []
    for i, row in enumerate(filtered, 1):
        errors.extend(validate_required(row, i))
    if errors:
        return {}, errors

    normalized = [normalize_row(r) for r in filtered]
    sorted_caps = sort_capabilities(normalized)

    index = {
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "type": "sharepoint_list_csv",
            "filename": Path(csv_path).name,
        },
        "counts": build_counts(sorted_caps),
        "capabilities": sorted_caps,
    }
    return index, []


# ── Summary markdown ────────────────────────────────────────────────────

def _expiring_soon(caps: list[dict], days: int = 14) -> list[dict]:
    """Return capabilities whose approval + cadence is within *days* of today."""
    now = datetime.datetime.utcnow()
    results = []
    for c in caps:
        date_str = c.get("latest_approved_date")
        cadence = c.get("review_cadence_days")
        if not date_str or cadence is None:
            continue
        try:
            approved = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        expiry = approved + datetime.timedelta(days=cadence)
        if expiry <= now + datetime.timedelta(days=days):
            results.append({**c, "_expiry": expiry.strftime("%Y-%m-%d")})
    return results


def build_summary_md(index: dict) -> str:
    """Generate a Markdown summary with Totals, Expiring Soon, Top Drift, Top Used."""
    caps = index["capabilities"]
    counts = index["counts"]
    lines = [
        "# MDPT Prompt Index Summary",
        "",
        f"**Generated:** {index['generated_at']}",
        f"**Source:** {index['source']['filename']}",
        "",
        "---",
        "",
        "## Totals",
        "",
        f"- **Capabilities included:** {counts['total']}",
    ]
    if counts.get("by_risk_lane"):
        for lane, cnt in sorted(counts["by_risk_lane"].items()):
            lines.append(f"- **{lane}:** {cnt}")
    if counts.get("by_use_case"):
        lines.append("")
        lines.append("**Top use cases:**")
        for entry in counts["by_use_case"]:
            lines.append(f"- {entry['use_case']}: {entry['count']}")

    # Expiring Soon
    lines.extend(["", "---", "", "## Expiring Soon", ""])
    expiring = _expiring_soon(caps)
    if expiring:
        lines.append("| Capability | Risk Lane | Expiry |")
        lines.append("|------------|-----------|--------|")
        for c in expiring:
            lines.append(f"| {c['capability_id']} — {c['title']} | {c['risk_lane']} | {c['_expiry']} |")
    else:
        lines.append("No capabilities expiring within 14 days.")

    # Top Drift
    lines.extend(["", "---", "", "## Top Drift", ""])
    with_drift = [c for c in caps if (c.get("telemetry", {}).get("drift_count") or 0) > 0]
    with_drift.sort(key=lambda c: c["telemetry"]["drift_count"], reverse=True)
    top_drift = with_drift[:5]
    if top_drift:
        lines.append("| Capability | Drift Count | Patch Count |")
        lines.append("|------------|-------------|-------------|")
        for c in top_drift:
            t = c["telemetry"]
            lines.append(f"| {c['capability_id']} — {c['title']} | {t['drift_count']} | {t.get('patch_count') or 0} |")
    else:
        lines.append("No drift events recorded.")

    # Top Used
    lines.extend(["", "---", "", "## Top Used", ""])
    with_runs = [c for c in caps if (c.get("telemetry", {}).get("run_count") or 0) > 0]
    with_runs.sort(key=lambda c: c["telemetry"]["run_count"], reverse=True)
    top_used = with_runs[:5]
    if top_used:
        lines.append("| Capability | Run Count | Last Eval Score |")
        lines.append("|------------|-----------|-----------------|")
        for c in top_used:
            t = c["telemetry"]
            score = t.get("last_eval_score")
            score_str = f"{score:.1f}" if score is not None else "—"
            lines.append(f"| {c['capability_id']} — {c['title']} | {t['run_count']} | {score_str} |")
    else:
        lines.append("No run telemetry recorded.")

    lines.append("")
    return "\n".join(lines)


# ── Schema validation ───────────────────────────────────────────────────

def validate_against_schema(index: dict) -> list[str]:
    """Validate the generated index against the JSON Schema. Returns errors."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text())
    validator = jsonschema.Draft7Validator(schema)
    return [
        f"Schema: {e.json_path}: {e.message}"
        for e in sorted(validator.iter_errors(index), key=lambda e: list(e.absolute_path))
    ]


# ── Orchestrator ────────────────────────────────────────────────────────

def generate(
    csv_path: str,
    out_dir: str,
    include_nonapproved: bool = False,
) -> int:
    """Main entry point. Returns exit code (0=success, 1=failure)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    index, errors = build_index(csv_path, include_nonapproved)
    if errors:
        print(f"FAIL — {len(errors)} validation error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    schema_errors = validate_against_schema(index)
    if schema_errors:
        print(f"FAIL — {len(schema_errors)} schema violation(s):", file=sys.stderr)
        for e in schema_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    json_path = out / "prompt_index.json"
    json_path.write_text(json.dumps(index, indent=2) + "\n")

    md_path = out / "prompt_index_summary.md"
    md_path.write_text(build_summary_md(index))

    print(f"OK — {index['counts']['total']} capabilities indexed")
    print(f"  JSON:    {json_path}")
    print(f"  Summary: {md_path}")
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_prompt_index",
        description="Generate MDPT Prompt Index from PromptCapabilities CSV export",
    )
    parser.add_argument("--csv", required=True, help="Path to PromptCapabilities CSV export")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument(
        "--include-nonapproved",
        action="store_true",
        help="Include non-Approved rows (default: Approved only)",
    )
    args = parser.parse_args(argv)
    return generate(args.csv, args.out, args.include_nonapproved)


if __name__ == "__main__":
    sys.exit(main())
