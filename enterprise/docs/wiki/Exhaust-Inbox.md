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
  │  → 3 Buckets     │  (rule-based or LLM-backed)
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

## LLM Extraction

By default the refiner uses **rule-based extraction** (keyword and pattern matching). Enable **LLM-backed extraction** using `claude-haiku-4-5-20251001` for higher-quality buckets:

```bash
pip install -e ".[exhaust-llm]"
export ANTHROPIC_API_KEY="sk-ant-..."
export EXHAUST_USE_LLM="1"
```

When enabled, the `LLMExtractor` in `engine/exhaust_llm_extractor.py` builds a transcript of episode events (truncated to 6 000 chars), calls the Anthropic Messages API with a JSON-only system prompt, and parses the structured response into TRUTH / REASONING / MEMORY items. All confidence values are clamped to `[0.0, 1.0]`.

**Fallback behaviour:** if the API call fails or returns unparseable output, the rule-based extractor runs transparently — no episode is lost and no error is surfaced.

**Grade expectation:** LLM extraction typically produces **B** or **A** grades for well-structured episodes; rule-based typically yields **C** or **D**.

Set `EXHAUST_USE_LLM=0` at any time to revert to rule-based without redeploying.

See also: [`engine/exhaust_llm_extractor.py`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/src/engine/exhaust_llm_extractor.py) and the [LLM extraction cookbook](https://github.com/8ryanWh1t3/DeepSigma/tree/main/enterprise/docs/cookbook/exhaust/llm_extraction/).

## Ingestion Wedges

### A) LangChain Real-Time

The `ExhaustCallbackHandler` extends the DeepSigma callback handler to emit `EpisodeEvent` payloads during chain execution. Events are buffered and flushed to the ingestion endpoint. Each LLM call also emits a `metric` event carrying `latency_ms` and the `model` name.

```python
from adapters.langchain_exhaust import ExhaustCallbackHandler

handler = ExhaustCallbackHandler(
    endpoint="http://localhost:8000/api/exhaust/events",
    project="my-project",
    team="ml-team",
)
chain.invoke(input, config={"callbacks": [handler]})
```

See: [`adapters/langchain_exhaust.py`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/src/adapters/langchain_exhaust.py)

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

See: [`adapters/anthropic_exhaust.py`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/src/adapters/anthropic_exhaust.py)

### C) Azure / OpenAI Batch

The batch adapter reads JSONL log exports from OpenAI or Azure OpenAI, normalises them to `EpisodeEvent` format, groups by `user_hash + conversation_id + time_window` (30 min default), and POSTs to the ingestion endpoint.

```bash
python -m adapters.azure_openai_exhaust \
    --input /path/to/logs.jsonl \
    --project my-project
```

See: [`adapters/azure_openai_exhaust.py`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/src/adapters/azure_openai_exhaust.py)

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
| `stale_reference` | Memory item references an episode ID no longer in the memory graph |

Each signal has a **severity** (Green / Yellow / Red) and a **fingerprint** (stable hash for dedup) with an optional `recommended_patch`.

## Coherence Scoring

Episodes receive a coherence score (0–100) computed from weighted dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| `claim_coverage` | 25% | How well claims cover the episode content |
| `evidence_quality` | 25% | Strength and specificity of evidence |
| `reasoning_completeness` | 20% | Whether decisions have rationale and alternatives |
| `memory_linkage` | 15% | Entity/relation extraction quality |
| `policy_adherence` | 15% | Compliance with active policy packs |

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
| `GET` | `/api/exhaust/health` | Health check — returns event/episode/refined counts |
| `POST` | `/api/exhaust/events` | Ingest a raw `EpisodeEvent` |
| `POST` | `/api/exhaust/episodes/assemble` | Group buffered events into episodes |
| `GET` | `/api/exhaust/episodes` | List all assembled episodes |
| `GET` | `/api/exhaust/episodes/{id}` | Episode detail |
| `POST` | `/api/exhaust/episodes/{id}/refine` | Extract buckets + drift + coherence score |
| `POST` | `/api/exhaust/episodes/{id}/commit` | Commit refined episode to Memory Graph |
| `PATCH` | `/api/exhaust/episodes/{id}/items/{item_id}` | Accept / reject / edit a single bucket item |
| `GET` | `/api/exhaust/mg` | Read the Memory Graph |
| `GET` | `/api/exhaust/drift` | List all drift signals |

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

## Diagrams

Four Mermaid diagrams cover the full Exhaust Inbox architecture:

| Diagram | Contents |
|---------|----------|
| [`archive/mermaid/29-exhaust-inbox-pipeline.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/29-exhaust-inbox-pipeline.md) | Full pipeline (graph TB), bucket extraction detail (flowchart), episode state machine (stateDiagram) |
| [`archive/mermaid/29-exhaust-connector-map.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/29-exhaust-connector-map.md) | Adapter ecosystem (graph LR), Source enum mapping, LangChain metric enrichment |
| [`archive/mermaid/29-exhaust-api-surface.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/29-exhaust-api-surface.md) | All 10 endpoints (graph TD), refine→commit sequence diagram, status codes |
| [`archive/mermaid/29-llm-extraction-flow.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/29-llm-extraction-flow.md) | LLMExtractor internals (flowchart), API call sequence, confidence clamping, system prompt |

## Related Pages

- [Architecture](Architecture) — Where RAL sits in the stack
- [Drift → Patch](Drift-to-Patch) — Drift detection and remediation lifecycle
- [Sealing & Episodes](Sealing-and-Episodes) — Episode sealing and immutability
- [Coherence Ops Mapping](Coherence-Ops-Mapping) — DLR/RS/DS/MG pipeline
- [LangChain](LangChain) — LangChain integration details
- [Unified Atomic Claims](Unified-Atomic-Claims) — Claim schema and primitives
- [Canon](Canon) — Blessed claim memory
