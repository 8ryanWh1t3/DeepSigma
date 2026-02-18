# Basic Ingest — Full Cycle Walkthrough

Demonstrates the complete Exhaust Inbox pipeline using the bundled sample
data: ingest → assemble → refine → commit.

**Time:** ~15 seconds
**Requires:** Running stack (`docker compose up -d` or uvicorn on :8000)
**No API key needed**

---

## Run it

```bash
bash cookbook/exhaust/basic_ingest/run.sh
```

Or step through manually:

### 1. Ingest sample events

```bash
while IFS= read -r line; do
  curl -s -X POST http://localhost:8000/api/exhaust/events \
    -H "Content-Type: application/json" \
    -d "$line" | jq -r '.status'
done < specs/sample_episode_events.jsonl
```

Expected output: `accepted` (×5 for sess-001 events)

### 2. Check health

```bash
curl -s http://localhost:8000/api/exhaust/health | jq .
```

### 3. Assemble episodes

```bash
curl -s -X POST http://localhost:8000/api/exhaust/episodes/assemble | jq .
# {"assembled": 1, "episode_ids": ["..."]}
```

### 4. List episodes and get the ID

```bash
curl -s http://localhost:8000/api/exhaust/episodes | jq '.episodes[0].episode_id'
```

### 5. Refine

```bash
EP_ID=$(curl -s http://localhost:8000/api/exhaust/episodes | jq -r '.episodes[0].episode_id')
curl -s -X POST "http://localhost:8000/api/exhaust/episodes/$EP_ID/refine" | jq '{grade: .grade, score: .coherence_score}'
```

### 6. Commit

```bash
curl -s -X POST "http://localhost:8000/api/exhaust/episodes/$EP_ID/commit" | jq .
# {"status": "committed", "episode_id": "..."}
```

---

## Expected output

| Step | Key field | Expected |
|------|-----------|---------|
| Ingest | `status` | `"accepted"` per event |
| Assemble | `assembled` | `1` |
| Refine | `grade` | `"C"` or higher |
| Commit | `status` | `"committed"` |

---

## Failure modes

| Symptom | Fix |
|---------|-----|
| `curl: connection refused` | Stack not running — `docker compose up -d` |
| `422 Unprocessable Entity` | Event payload doesn't match schema — check `event_type` enum |
| `assembled: 0` | Events not yet ingested — repeat step 1 |
