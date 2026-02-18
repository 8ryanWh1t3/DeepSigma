# Exhaust Inbox – Quickstart

> Capture chat exhaust from AI interactions and refine it into **TRUTH**, **REASONING**, and **MEMORY** buckets.

## 1. Start the stack

```bash
docker compose up -d
```

The dashboard is available at `http://localhost:5173` and the API at `http://localhost:8000`.

## 2. Open the Inbox

Navigate to:

```
http://localhost:5173/#/inbox
```

This renders the three-lane Exhaust Inbox UI:
- **Left lane** – Episode stream with filters (project, team, source, drift, confidence)
- **Center lane** – Episode detail timeline (prompt/tool/response/metric/error chips)
- **Right lane** – Bucket panel with TRUTH / REASONING / MEMORY tabs

## 3. Ingest sample events

Post the included sample data:

```bash
python tools/exhaust_cli.py import --file specs/sample_episode_events.jsonl
```

Or use curl directly:

```bash
curl -X POST http://localhost:8000/api/exhaust/events \
  -H "Content-Type: application/json" \
  -d @specs/sample_episode_events.jsonl
```

## 4. Assemble episodes

Group raw events into decision episodes:

```bash
python tools/exhaust_cli.py assemble
```

## 5. Refine & commit

Refine an episode to extract truth/reasoning/memory:

```bash
# List episodes to get IDs
python tools/exhaust_cli.py list

# Refine a specific episode
python tools/exhaust_cli.py refine --episode <episode_id>

# Commit after review
python tools/exhaust_cli.py commit --episode <episode_id>
```

Or use the UI: select an episode → click **Refine** → review bucket items → **Accept All** → **Commit**.

## 6. Check health

```bash
python tools/exhaust_cli.py health
# or
curl http://localhost:8000/api/exhaust/health
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/exhaust/events` | Ingest raw events |
| POST | `/api/exhaust/episodes/assemble` | Group events → episodes |
| GET | `/api/exhaust/episodes` | List episodes (with filters) |
| GET | `/api/exhaust/episodes/{id}` | Episode detail |
| POST | `/api/exhaust/episodes/{id}/refine` | Extract truth/reasoning/memory |
| POST | `/api/exhaust/episodes/{id}/commit` | Commit refined episode |
| POST | `/api/exhaust/episodes/{id}/item` | Accept/reject/edit single item |
| GET | `/api/exhaust/drift` | List drift signals |
| GET | `/api/exhaust/health` | Health check |
| GET | `/api/exhaust/schema` | JSON Schema export |

## Connectors

### LangChain (real-time)

```python
from adapters.langchain_exhaust import ExhaustCallbackHandler

handler = ExhaustCallbackHandler(
    endpoint="http://localhost:8000/api/exhaust/events",
    project="my-project",
    team="ml-team",
)
chain.invoke(input, config={"callbacks": [handler]})
```

### Azure / OpenAI (batch)

```bash
python -m adapters.azure_openai_exhaust \
    --input /path/to/openai_logs.jsonl \
    --endpoint http://localhost:8000/api/exhaust/events \
    --project my-project
```

## Confidence gating

| Score | Tier | Action |
|-------|------|--------|
| ≥ 0.85 | auto_commit | Green – automatically committed |
| 0.65 – 0.84 | review_required | Amber – human review needed |
| < 0.65 | hold | Red – held for investigation |

## Coherence grading

| Score | Grade |
|-------|-------|
| ≥ 85 | A |
| ≥ 75 | B |
| ≥ 65 | C |
| < 65 | D |

## LLM Extraction (optional)

By default the refiner uses fast rule-based extraction. For higher-quality
TRUTH/REASONING/MEMORY output, enable Anthropic-backed extraction:

```bash
pip install -e ".[exhaust-llm]"
export ANTHROPIC_API_KEY="sk-ant-..."
export EXHAUST_USE_LLM="1"
```

When `EXHAUST_USE_LLM=1`, each `/refine` call sends the episode transcript
to `claude-haiku-4-5-20251001` and parses structured JSON back into buckets.
If the API is unavailable or the key is missing, the rule-based extractor
runs automatically as a fallback — no episode is lost.

To verify LLM extraction is active:

```bash
curl -s http://localhost:8000/api/exhaust/episodes/<id>/refine | jq '.grade'
# LLM extraction typically yields higher coherence scores (B/A vs C/D)
```

The model is configurable in code:

```python
from engine.exhaust_llm_extractor import LLMExtractor
extractor = LLMExtractor(model="claude-sonnet-4-5-20250929")
buckets = extractor.extract(episode)
```

## Storage (MVP)

All data is file-based under `/app/data`:

- `events.jsonl` – append-only raw events
- `episodes/{id}.json` – assembled episodes
- `refined/{id}.json` – refined episodes
- `mg/memory_graph.jsonl` – memory graph entries
- `drift/drift.jsonl` – drift signals
