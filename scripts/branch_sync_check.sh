#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "FAIL: base ref not found: $BASE_REF"
  echo "Hint: run 'git fetch --prune origin' first."
  exit 2
fi

if ! git rev-parse --verify "$HEAD_REF" >/dev/null 2>&1; then
  echo "FAIL: head ref not found: $HEAD_REF"
  exit 2
fi

if git merge-base --is-ancestor "$BASE_REF" "$HEAD_REF"; then
  echo "PASS: $HEAD_REF contains $BASE_REF (branch is up to date with base)."
  exit 0
fi

echo "FAIL: $HEAD_REF is behind $BASE_REF."
echo "Update your branch before merge:"
echo "  git fetch origin"
echo "  git rebase $BASE_REF"
exit 1
