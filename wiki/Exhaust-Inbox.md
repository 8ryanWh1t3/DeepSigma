# Exhaust Inbox

The **Exhaust Inbox** captures chat exhaust from hundreds of users interacting with AI and automatically refines it into three canonical buckets: **TRUTH**, **REASONING**, and **MEMORY**.

## Overview

Every AI interaction produces exhaust — prompts, responses, tool calls, metrics, and errors. The Exhaust Inbox system ingests this raw stream, groups it into **Decision Episodes**, and runs extraction/refinement to produce structured, confidence-gated knowledge items.

```text
  Raw Events (JSONL)
        |
        v
  ┌─────────────────┐
  │  Ingest & Group  │  POST /api/exhaust/events
  │  → Episodes      │  POST /api/exhaust/episodes/assemble
  └─────────────────┘
        |
        v
  ┌─────────────────┐
  │  Refine          │  POST /api/exhaust/episodes/{id}/refine
  │  → 3 Buckets     │
  │  → Drift Signals │
  │  → Coherence     │
  └─────────────────┘
        |
        v
  ┌─────────────────┐
  │  Review & Commit │  Human-in-the-loop or auto-commit
  │  → Memory Graph  │  POST /api/exhaust/episodes/{id}/commit
  └─────────────────┘
```

## Three Buckets

| Bucket | Contains | Example |
|--------|----------|---------|
| **TRUTH** | Atomic claims, evidence, metrics | "service-alpha is running v2.4.1 with 3 replicas" |
| **REASONING** | Decisions, assumptions, alternatives, rationale | "Recommend monitoring 30 more minutes before rollback" |
| **MEMORY** | Entities, relations, artifacts, context pointers | "service-alpha → deployed_by → ml-ops team" |

Each item has a **confidence score** (0–1) that determines its gating tier:

| Score | Tier | Action |
|-------|------|--------|
| ≥ 0.85 | `auto_commit` | Automatically committed (green) |
| 0.65 – 0.84 | `review_required` | Human review needed (amber) |
| < 0.65 | `hold` | Held for investigation (red) |

## Ingestion Wedges

### A) LangChain Real-Time

The `ExhaustCallbackHandler` extends the DeepSigma callback handler to emit `EpisodeEvent` payloads during chain execution. Events are buffered and flushed to the ingestion endpoint.

```python
from adapters.langchain_exhaust import ExhaustCallbackHandler

handler = ExhaustCallbackHandler(
    endpoint="http://localhost:8000/api/exhaust/events",
    project="my-project",
    team="ml-team",
)
chain.invoke(input, config={"callbacks": [handler]})
```

See: [`adapters/langchain_exhaust.py`](../adapters/langchain_exhaust.py)

### B) Anthropic Direct

The Anthropic batch adapter reads JSONL exports of Anthropic Messages API
responses, normalises them to `EpisodeEvent` format (prompt / completion /
tool / metric), groups by `session_id + time_window` (30 min default), and
POSTs to the ingestion endpoint.

```bash
python -m adapters.anthropic_exhaust \
    --file /path/to/anthropic_logs.jsonl \
    --project my-project \
    --dry-run          # preview without POSTing
```

See: [`adapters/anthropic_exhaust.py`](../adapters/anthropic_exhaust.py)

### E) Azure / OpenAI Batch

The batch adapter reads JSONL log exports from OpenAI or Azure OpenAI, normalises them to `EpisodeEvent` format, groups by `user_hash + conversation_id + time_window` (30 min default), and POSTs to the ingestion endpoint.

```bash
python -m adapters.azure_openai_exhaust \
    --input /path/to/logs.jsonl \
    --project my-project
```

See: [`adapters/azure_openai_exhaust.py`](../adapters/azure_openai_exhaust.py)

## Episode Lifecycle

1. **Ingest** — Raw events arrive via POST or file import
2. **Assemble** — Events are grouped into Decision Episodes by `session_id + user_hash + time_window`
3. **Refine** — The refiner extracts truth/reasoning/memory items, detects drift, computes coherence
4. **Review** — Human reviews items in the three-lane UI (or auto-commit for high-confidence items)
5. **Commit** — Accepted items flow into the Memory Graph; drift signals feed the Drift→Patch loop

## Drift Detection

The refiner performs MVP drift detection on each episode:

| Signal Type | Description |
|-------------|-------------|
| `contradiction` | Claim contradicts existing canon |
| `missing_policy` | Required policy flag not present |
| `low_coverage` | Insufficient claim coverage for the episode |
| `stale_reference` | References outdated or expired data |

Each signal has a **severity** (Green / Yellow / Red) and a **fingerprint** (stable hash for dedup) with an optional `recommended_patch`.

## Coherence Scoring

Episodes receive a coherence score (0–100) computed from weighted dimensions:

| Dimension | Description |
|-----------|-------------|
| `claim_coverage` | How well claims cover the episode content |
| `evidence_quality` | Strength and specificity of evidence |
| `reasoning_completeness` | Whether decisions have rationale and alternatives |
| `memory_linkage` | Entity/relation extraction quality |
| `policy_adherence` | Compliance with active policy packs |

**Grade mapping:** A ≥ 85, B ≥ 75, C ≥ 65, D < 65

## Dashboard UI

The Exhaust Inbox renders as a **three-lane layout** at `#/inbox`:

| Lane | Component | Content |
|------|-----------|---------|
| **Left** | `EpisodeStream` | Scrollable list of episode cards with filters |
| **Center** | `EpisodeDetail` | Timeline view of events (prompt / tool / response chips) |
| **Right** | `BucketPanel` | Tabbed TRUTH / REASONING / MEMORY with accept/reject/edit |

### Filters
- Project, Team, Source (text)
- Coherence score range (0–100)
- Drift-only toggle
- Low-confidence-only toggle

### Actions
- **Accept** / **Reject** / **Edit** individual items
- **Accept All** — bulk accept pending items
- **Escalate** — flag for senior review
- **Commit** — persist refined episode to storage

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/exhaust/events` | Ingest raw events |
| `POST` | `/api/exhaust/episodes/assemble` | Group events into episodes |
| `GET` | `/api/exhaust/episodes` | List episodes (filterable) |
| `GET` | `/api/exhaust/episodes/{id}` | Episode detail |
| `POST` | `/api/exhaust/episodes/{id}/refine` | Extract buckets + drift + coherence |
| `POST` | `/api/exhaust/episodes/{id}/commit` | Commit refined episode |
| `POST` | `/api/exhaust/episodes/{id}/item` | Accept/reject/edit single item |
| `GET` | `/api/exhaust/drift` | List drift signals |
| `GET` | `/api/exhaust/health` | Health check |
| `GET` | `/api/exhaust/schema` | JSON Schema export |

## Storage (MVP)

File-based under `/app/data` (single-writer, `uvicorn --workers 1`):

| Path | Format | Description |
|------|--------|-------------|
| `events.jsonl` | Append-only JSONL | Raw ingested events |
| `episodes/{id}.json` | JSON per episode | Assembled episodes |
| `refined/{id}.json` | JSON per episode | Refined episodes with buckets |
| `mg/memory_graph.jsonl` | Append-only JSONL | Committed memory graph entries |
| `drift/drift.jsonl` | Append-only JSONL | Drift signals |

## CLI

```bash
python tools/exhaust_cli.py import --file specs/sample_episode_events.jsonl
python tools/exhaust_cli.py assemble
python tools/exhaust_cli.py list
python tools/exhaust_cli.py refine --episode <id>
python tools/exhaust_cli.py commit --episode <id>
python tools/exhaust_cli.py health
```

## Related Pages

- [Architecture](Architecture) — Where RAL sits in the stack
- [Drift → Patch](Drift-to-Patch) — Drift detection and remediation lifecycle
- [Sealing & Episodes](Sealing-and-Episodes) — Episode sealing and immutability
- [Coherence Ops Mapping](Coherence-Ops-Mapping) — DLR/RS/DS/MG pipeline
- [LangChain](LangChain) — LangChain integration details
- [Unified Atomic Claims](Unified-Atomic-Claims) — Claim schema and primitives
- [Canon](Canon) — Blessed claim memory
