#!/usr/bin/env bash
set -euo pipefail

OUTDIR="release_kpis"
mkdir -p "$OUTDIR"

echo "[issues-review] exporting open issues JSON"
if gh issue list --state open --limit 500 \
  --json number,title,labels,createdAt,updatedAt,url,assignees,author \
  > "$OUTDIR/issues_open.json"; then
  echo "[issues-review] wrote $OUTDIR/issues_open.json"
else
  echo "[issues-review] JSON export failed; writing plaintext fallback"
  gh issue list --state open --limit 500 > "$OUTDIR/issues_open.txt"
  exit 1
fi

echo "[issues-review] exporting closed issues (last 30d) JSON"
if gh issue list --state closed --limit 500 \
  --search "closed:>=@today-30" \
  --json number,title,labels,createdAt,closedAt,url,assignees,author \
  > "$OUTDIR/issues_closed_30d.json"; then
  echo "[issues-review] wrote $OUTDIR/issues_closed_30d.json"
else
  echo "[issues-review] closed JSON export failed; writing plaintext fallback"
  gh issue list --state closed --limit 500 --search "closed:>=@today-30" > "$OUTDIR/issues_closed_30d.txt"
fi

echo "[issues-review] generating KPI issue brief artifacts"
python scripts/issues_brief.py

echo "[issues-review] done"
