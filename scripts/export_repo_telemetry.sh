#!/usr/bin/env bash
set -euo pipefail

mkdir -p release_kpis

# Issues (all states) for weighted effort and committee/security labeling.
gh issue list --state all --limit 1000 \
  --json number,title,labels,createdAt,closedAt,url \
  > release_kpis/issues_all.json

# Merged PR telemetry for integration overhead and churn metadata.
gh pr list --state merged --limit 1000 \
  --json number,title,labels,createdAt,mergedAt,url,additions,deletions,changedFiles \
  > release_kpis/prs_merged.json
