#!/usr/bin/env bash
# cookbook/exhaust/basic_ingest/run.sh
# Full Exhaust Inbox cycle: ingest → assemble → refine → commit
# Requires: running stack on localhost:8000; jq installed
set -euo pipefail

BASE_URL="${EXHAUST_API:-http://localhost:8000}"
SAMPLE_FILE="specs/sample_episode_events.jsonl"

echo "=== Exhaust Basic Ingest Cookbook ==="
echo "API: $BASE_URL"
echo

# ── 0. Health check ────────────────────────────────────────────────
echo "[ 0 ] Health check"
curl -sf "$BASE_URL/api/exhaust/health" | jq '{status, events_count, episodes_count}'
echo

# ── 1. Ingest sess-001 events from sample file ─────────────────────
echo "[ 1 ] Ingesting sess-001 events from $SAMPLE_FILE"
COUNT=0
while IFS= read -r line; do
  SESSION=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
  if [ "$SESSION" = "sess-001" ]; then
    STATUS=$(curl -sf -X POST "$BASE_URL/api/exhaust/events" \
      -H "Content-Type: application/json" \
      -d "$line" | jq -r '.status')
    echo "  → $STATUS"
    COUNT=$((COUNT + 1))
  fi
done < "$SAMPLE_FILE"
echo "  Ingested $COUNT events"
echo

# ── 2. Assemble episodes ───────────────────────────────────────────
echo "[ 2 ] Assembling episodes"
ASSEMBLE=$(curl -sf -X POST "$BASE_URL/api/exhaust/episodes/assemble")
echo "$ASSEMBLE" | jq '{assembled, episode_ids}'
echo

# ── 3. Get episode ID ──────────────────────────────────────────────
EP_ID=$(curl -sf "$BASE_URL/api/exhaust/episodes" | jq -r '.episodes[0].episode_id')
if [ -z "$EP_ID" ] || [ "$EP_ID" = "null" ]; then
  echo "ERROR: No episode found. Check that events were ingested."
  exit 1
fi
echo "[ 3 ] Episode ID: $EP_ID"
echo

# ── 4. Refine ──────────────────────────────────────────────────────
echo "[ 4 ] Refining episode"
REFINED=$(curl -sf -X POST "$BASE_URL/api/exhaust/episodes/$EP_ID/refine")
echo "$REFINED" | jq '{status, grade, coherence_score}'
echo

# ── 5. Commit ──────────────────────────────────────────────────────
echo "[ 5 ] Committing episode"
curl -sf -X POST "$BASE_URL/api/exhaust/episodes/$EP_ID/commit" | jq '{status, episode_id}'
echo

# ── 6. Final health ────────────────────────────────────────────────
echo "[ 6 ] Final health (should show events > 0, refined > 0)"
curl -sf "$BASE_URL/api/exhaust/health" | jq '{events_count, episodes_count, refined_count}'
echo

echo "=== Done ==="
