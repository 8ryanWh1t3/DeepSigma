# Exhaust Inbox Cookbook

Runnable, end-to-end examples for ingesting AI interaction exhaust into the
Σ OVERWATCH Exhaust Inbox and refining it into TRUTH / REASONING / MEMORY.

---

## Quick chooser

| I have… | Use |
|---------|-----|
| A running LangChain app | [LangChain real-time](../../adapters/langchain_exhaust.py) |
| OpenAI / Azure OpenAI log files | [Azure/OpenAI batch adapter](../../adapters/azure_openai_exhaust.py) |
| Anthropic Messages API log files | [Anthropic batch adapter](../../adapters/anthropic_exhaust.py) |
| Raw events to POST by hand | [basic_ingest/](basic_ingest/) |
| Anthropic API key + want better extraction | [llm_extraction/](llm_extraction/) |

---

## Prerequisites

```bash
docker compose up -d          # starts API on :8000 and dashboard on :5173
# or: uvicorn dashboard.server.main:app --port 8000
```

Verify the stack is up:

```bash
curl -s http://localhost:8000/api/exhaust/health | jq .
# {"status": "ok", "events_count": 0, ...}
```

---

## Recipes

### [basic_ingest/](basic_ingest/)
Full ingest → assemble → refine → commit cycle using the sample JSONL file.
No API key required. Runs in under 30 seconds.

### [llm_extraction/](llm_extraction/)
Same cycle but with `EXHAUST_USE_LLM=1` enabled, using claude-haiku to
extract higher-quality buckets. Requires `ANTHROPIC_API_KEY`.

---

## Verification concept

Every example produces a final output you can compare against:

```bash
curl -s http://localhost:8000/api/exhaust/health | jq '{events: .events_count, episodes: .episodes_count, refined: .refined_count}'
```

Expected after `basic_ingest/run.sh`:
```json
{"events": 5, "episodes": 1, "refined": 1}
```
