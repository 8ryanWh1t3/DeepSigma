#!/usr/bin/env bash
set -euo pipefail

# ==============================
# DeepSigma Roadmap Alignment Audit (A-D)
# Requires: gh, python3
# Usage:
#   ./scripts/roadmap_audit.sh
# Optional:
#   APPLY_FIXES=true ./scripts/roadmap_audit.sh   # apply suggested labels
#   BASE_BRANCH=main ./scripts/roadmap_audit.sh
# ==============================

APPLY_FIXES="${APPLY_FIXES:-false}"
BASE_BRANCH="${BASE_BRANCH:-main}"

OUT_DIR="release_kpis/roadmap_audit"
mkdir -p "$OUT_DIR"

echo "Roadmap Alignment Audit (A-D)"
echo "  APPLY_FIXES=$APPLY_FIXES"
echo "  BASE_BRANCH=$BASE_BRANCH"
echo ""

# ------------------------------
# A) Ensure label taxonomy exists
# ------------------------------
echo "A) Ensuring labels exist (taxonomy check)..."

REQUIRED_LABELS=(
  "roadmap"
  "epic"
  "milestone"
  "hardening"
  "integration"
  "credibility"
  "adoption"
  "stability"
  "metrics"
  "security"
  "governance"
  "ci"
  "tec"
  "dormant"
  "type:feature"
  "type:bug"
  "type:spec"
  "type:debt"
  "sev:P0"
  "sev:P1"
  "sev:P2"
  "sev:P3"
  "v2.0.7"
  "v2.1.0"
  "v2.1.1"
  "kpi:technical_completeness"
  "kpi:automation_depth"
  "kpi:authority_modeling"
  "kpi:enterprise_readiness"
  "kpi:operational_maturity"
  "kpi:economic_measurability"
  "kpi:data_integration"
  "kpi:scalability"
)

# Fetch existing labels
gh label list --limit 1000 --json name > "$OUT_DIR/labels_existing.json"

REQ_LABELS="$(printf "%s\n" "${REQUIRED_LABELS[@]}")" python3 - <<'PY'
import json, os
from pathlib import Path

out_dir = Path("release_kpis/roadmap_audit")
existing = {l["name"] for l in json.loads((out_dir/"labels_existing.json").read_text(encoding="utf-8"))}
required = [x.strip() for x in os.environ.get("REQ_LABELS", "").splitlines() if x.strip()]
missing = [x for x in required if x not in existing]

(out_dir/"labels_missing.json").write_text(json.dumps(missing, indent=2), encoding="utf-8")
print(f"  Existing labels: {len(existing)}")
print(f"  Missing required labels: {len(missing)}")
PY

MISSING_COUNT="$(python3 - <<'PY'
import json
from pathlib import Path
missing = json.loads((Path("release_kpis/roadmap_audit")/"labels_missing.json").read_text(encoding="utf-8"))
print(len(missing))
PY
)"

if [ "$MISSING_COUNT" -gt 0 ]; then
  echo "  Missing labels detected: $MISSING_COUNT"
  echo "  Writing: $OUT_DIR/labels_missing.json"
  if [ "$APPLY_FIXES" = "true" ]; then
    echo "  APPLY_FIXES=true -> creating missing labels..."
    python3 - <<'PY'
import json, subprocess
from pathlib import Path
missing = json.loads((Path("release_kpis/roadmap_audit")/"labels_missing.json").read_text(encoding="utf-8"))
for name in missing:
    subprocess.run(["gh","label","create",name,"--color","ededed"], check=False)
print("  Done creating missing labels (non-fatal if already existed).")
PY
  else
    echo "  (Read-only) Run with APPLY_FIXES=true to auto-create labels."
  fi
else
  echo "  Labels aligned"
fi

echo ""

# ------------------------------
# Pull issues + PRs
# ------------------------------
echo "Fetching issues + PRs (telemetry)..."
gh issue list --state all --limit 2000 --json number,title,labels,state,createdAt,closedAt,url,assignees,author > "$OUT_DIR/issues_all.json"
gh pr list --state all --limit 2000 --json number,title,labels,state,createdAt,mergedAt,url,author > "$OUT_DIR/prs_all.json"
echo "  Saved: $OUT_DIR/issues_all.json, $OUT_DIR/prs_all.json"
echo ""

# ------------------------------
# B) Generate milestone grouping view (version + epic)
# ------------------------------
echo "B) Generating milestone grouping (by version + epic)..."

python3 - <<'PY'
import json
from pathlib import Path

out = Path("release_kpis/roadmap_audit")
issues = json.loads((out/"issues_all.json").read_text(encoding="utf-8"))

def lbls(x):
    return [l["name"] for l in x.get("labels", [])]

VERS = ["v2.0.7","v2.1.0","v2.1.1"]

def version(l):
    for v in VERS:
        if v in l:
            return v
    return "UNVERSIONED"

groups = {}
for it in issues:
    l = lbls(it)
    v = version(l)
    e = "EPIC" if "epic" in l or it["title"].strip().upper().startswith("EPIC:") else "ISSUE"
    groups.setdefault(v, {}).setdefault(e, []).append(it)

md = ["# Roadmap Grouping (Issues)", ""]
for v in ["v2.0.7","v2.1.0","v2.1.1","UNVERSIONED"]:
    if v not in groups:
        continue
    md.append(f"## {v}")
    for e in ["EPIC","ISSUE"]:
        items = sorted(groups[v].get(e, []), key=lambda x: x["number"])
        if not items:
            continue
        md.append(f"### {e}s ({len(items)})")
        for it in items:
            labs = ", ".join(lbls(it))
            md.append(f"- #{it['number']} **{it['title']}**  ")
            md.append(f"  labels: {labs}")
        md.append("")

(out/"ROADMAP_GROUPING.md").write_text("\n".join(md), encoding="utf-8")
print("  Wrote: release_kpis/roadmap_audit/ROADMAP_GROUPING.md")
PY

echo ""

# ------------------------------
# C) Detect redundant issues (suggest merges)
# ------------------------------
echo "C) Detecting likely redundant issues (suggest merges)..."

python3 - <<'PY'
import json
from pathlib import Path
from difflib import SequenceMatcher

out = Path("release_kpis/roadmap_audit")
issues = json.loads((out/"issues_all.json").read_text(encoding="utf-8"))

def lbls(x):
    return [l["name"] for l in x.get("labels", [])]

def version(l):
    for v in ["v2.0.7","v2.1.0","v2.1.1"]:
        if v in l:
            return v
    return "UNVERSIONED"

open_issues = [i for i in issues if i.get("state") == "OPEN"]
pairs = []
for i in range(len(open_issues)):
    for j in range(i + 1, len(open_issues)):
        a, b = open_issues[i], open_issues[j]
        if version(lbls(a)) != version(lbls(b)):
            continue
        ta, tb = a["title"].lower(), b["title"].lower()
        sim = SequenceMatcher(None, ta, tb).ratio()
        if sim >= 0.84:
            pairs.append((sim, a, b))

pairs.sort(key=lambda x: -x[0])
suggest = []
for sim, a, b in pairs[:50]:
    suggest.append(
        {
            "similarity": round(sim, 3),
            "version": version(lbls(a)),
            "a": {"number": a["number"], "title": a["title"]},
            "b": {"number": b["number"], "title": b["title"]},
            "note": "Likely overlap; consider merging scope or linking as duplicates.",
        }
    )

(out/"REDUNDANCY_SUGGESTIONS.json").write_text(json.dumps(suggest, indent=2), encoding="utf-8")
md = ["# Redundancy Suggestions (Top 50)", ""]
for s in suggest:
    md.append(
        f"- ({s['similarity']}) {s['version']}: #{s['a']['number']} **{s['a']['title']}**  <->  #{s['b']['number']} **{s['b']['title']}**"
    )

(out/"REDUNDANCY_SUGGESTIONS.md").write_text("\n".join(md), encoding="utf-8")
print("  Wrote: release_kpis/roadmap_audit/REDUNDANCY_SUGGESTIONS.json/.md")
PY

echo ""

# ------------------------------
# D) Create version-based dashboard summary + misalignment report
# ------------------------------
echo "D) Creating alignment dashboard + misalignment report..."

python3 - <<'PY'
import json
from pathlib import Path

out = Path("release_kpis/roadmap_audit")
issues = json.loads((out/"issues_all.json").read_text(encoding="utf-8"))

KPI_LABELS = [
  "kpi:technical_completeness",
  "kpi:automation_depth",
  "kpi:authority_modeling",
  "kpi:enterprise_readiness",
  "kpi:operational_maturity",
  "kpi:economic_measurability",
  "kpi:data_integration",
  "kpi:scalability",
]
VERS = ["v2.0.7","v2.1.0","v2.1.1"]

def lbls(x):
    return [l["name"] for l in x.get("labels", [])]

def bucket_version(l):
    for v in VERS:
        if v in l:
            return v
    return "UNVERSIONED"

def track(l):
    if "stability" in l:
        return "STABILITY"
    if "integration" in l:
        return "INTEGRATION"
    if "security" in l:
        return "SECURITY"
    if "credibility" in l:
        return "CREDIBILITY"
    if "adoption" in l:
        return "ADOPTION"
    if "governance" in l or "hardening" in l:
        return "HARDENING"
    return "GENERAL"

summary = {v: {"OPEN":0,"CLOSED":0,"EPIC":0,"kpi":{k:0 for k in KPI_LABELS},"tracks":{}} for v in VERS+["UNVERSIONED"]}
misaligned = []

for it in issues:
    l = lbls(it)
    v = bucket_version(l)
    state = it.get("state", "OPEN")
    if state not in ("OPEN", "CLOSED"):
        state = "OPEN"
    summary[v][state] += 1

    if "epic" in l or it["title"].strip().upper().startswith("EPIC:"):
        summary[v]["EPIC"] += 1

    for k in KPI_LABELS:
        if k in l:
            summary[v]["kpi"][k] += 1

    tr = track(l)
    summary[v]["tracks"][tr] = summary[v]["tracks"].get(tr, 0) + 1

    if state == "OPEN":
        if v == "UNVERSIONED":
            misaligned.append({"number": it["number"], "title": it["title"], "reason":"Open issue missing version label"})
        if v == "v2.0.7" and tr == "INTEGRATION":
            misaligned.append({"number": it["number"], "title": it["title"], "reason":"Integration tagged in v2.0.7 (should usually be v2.1.1)"})
        if v == "v2.1.1" and tr == "STABILITY":
            misaligned.append({"number": it["number"], "title": it["title"], "reason":"Stability tagged in v2.1.1 (should usually be v2.0.7)"})

(out/"ROADMAP_DASHBOARD.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(out/"MISALIGNMENTS.json").write_text(json.dumps(misaligned, indent=2), encoding="utf-8")

md = ["# Roadmap Alignment Dashboard", ""]
for v in ["v2.0.7","v2.1.0","v2.1.1","UNVERSIONED"]:
    s = summary[v]
    md.append(f"## {v}")
    md.append(f"- Open: **{s['OPEN']}** | Closed: **{s['CLOSED']}** | Epics: **{s['EPIC']}**")
    md.append("")
    md.append("### Tracks")
    for k in sorted(s["tracks"].keys()):
        md.append(f"- {k}: **{s['tracks'][k]}**")
    md.append("")
    md.append("### KPI Coverage (issue count)")
    for k in KPI_LABELS:
        md.append(f"- {k}: **{s['kpi'][k]}**")
    md.append("")

md.append("## Misalignments")
md.append(f"- Count: **{len(misaligned)}**")
for m in misaligned[:50]:
    md.append(f"- #{m['number']} **{m['title']}** - {m['reason']}")
if len(misaligned) > 50:
    md.append(f"- ...and {len(misaligned)-50} more (see MISALIGNMENTS.json)")

(out/"ROADMAP_DASHBOARD.md").write_text("\n".join(md), encoding="utf-8")

print("  Wrote: release_kpis/roadmap_audit/ROADMAP_DASHBOARD.md/.json")
print("  Wrote: release_kpis/roadmap_audit/MISALIGNMENTS.json")
PY

echo ""
echo "Done."
echo "Outputs:"
echo " - $OUT_DIR/ROADMAP_GROUPING.md"
echo " - $OUT_DIR/REDUNDANCY_SUGGESTIONS.md"
echo " - $OUT_DIR/ROADMAP_DASHBOARD.md"
echo " - $OUT_DIR/MISALIGNMENTS.json"
echo ""
echo "Next: If you want auto-relabel suggestions applied, run:"
echo "  APPLY_FIXES=true ./scripts/roadmap_audit.sh"
