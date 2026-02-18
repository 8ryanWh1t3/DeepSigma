# Exhaust API Surface

All ten REST endpoints exposed by `dashboard/server/exhaust_api.py`, grouped by resource.

```mermaid
graph TD
    ROOT["/api/exhaust"] --> H
    ROOT --> EV
    ROOT --> EP
    ROOT --> IT
    ROOT --> MG2
    ROOT --> DR

    subgraph Health["Health"]
        H["GET /health\n──────────────\nReturns: status, events_count,\nepisodes_count, refined_count\n200 OK"]
    end

    subgraph Events["Events"]
        EV["POST /events\n──────────────\nBody: EpisodeEvent (JSON)\nReturns: {status: accepted}\n200 OK · 422 Unprocessable"]
    end

    subgraph Episodes["Episodes"]
        EP --> LIST["GET /episodes\n──────────────\nReturns: {episodes: [DecisionEpisode]}\n200 OK"]
        EP --> ASM["POST /episodes/assemble\n──────────────\nGroups buffered events by session_id\nReturns: {assembled: N, episode_ids: [...]}\n200 OK"]
        EP --> GET1["GET /episodes/{episode_id}\n──────────────\nReturns: DecisionEpisode\n200 OK · 404 Not Found"]
        EP --> REFINE["POST /episodes/{episode_id}/refine\n──────────────\nRuns rule-based (or LLM if EXHAUST_USE_LLM=1)\nReturns: RefinedEpisode\n{truth, reasoning, memory,\ndrift_signals, coherence_score, grade}\n200 OK · 404 Not Found"]
        EP --> COMMIT["POST /episodes/{episode_id}/commit\n──────────────\nWrites to MG + Drift Log\nReturns: {status: committed, episode_id}\n200 OK · 404 Not Found · 400 Not Refined"]
    end

    subgraph Items["Item Actions"]
        IT["PATCH /episodes/{episode_id}/items/{item_id}\n──────────────\nBody: ItemAction {action: accept|reject|edit,\n       item_type: truth|reasoning|memory,\n       updated_value: str?}\nReturns: {status: ok, item_id, action}\n200 OK · 404 Not Found"]
    end

    subgraph MG["Memory Graph"]
        MG2["GET /mg\n──────────────\nReturns: {nodes: [MemoryItem]}\n200 OK"]
    end

    subgraph Drift["Drift Log"]
        DR["GET /drift\n──────────────\nReturns: {signals: [DriftSignal]}\n200 OK"]
    end

    style Health fill:#1a1a2e,stroke:#e94560,color:#fff
    style Events fill:#16213e,stroke:#0f3460,color:#fff
    style Episodes fill:#162447,stroke:#e94560,color:#fff
    style Items fill:#0f3460,stroke:#533483,color:#fff
    style MG fill:#16213e,stroke:#533483,color:#fff
    style Drift fill:#1a1a2e,stroke:#533483,color:#fff
```

## Request / Response Flow

How a typical refine → item-action → commit sequence flows through the API.

```mermaid
sequenceDiagram
    participant Client
    participant API as exhaust_api.py
    participant Refiner as exhaust_refiner.py
    participant LLM as LLMExtractor (optional)
    participant Store as File Store (data/)

    Client->>API: POST /events (×N)
    API->>Store: append events.jsonl
    API-->>Client: {status: accepted} ×N

    Client->>API: POST /episodes/assemble
    API->>Store: read events.jsonl, group by session_id
    API->>Store: write episodes/{id}.json
    API-->>Client: {assembled: 1, episode_ids: [...]}

    Client->>API: POST /episodes/{id}/refine
    API->>Refiner: refine_episode(episode, use_llm)
    alt EXHAUST_USE_LLM=1
        Refiner->>LLM: LLMExtractor().extract(episode)
        LLM-->>Refiner: {truth, reasoning, memory}
    else default
        Refiner->>Refiner: rule-based extraction
    end
    Refiner-->>API: RefinedEpisode
    API->>Store: write refined/{id}.json
    API-->>Client: RefinedEpisode JSON

    Client->>API: PATCH /episodes/{id}/items/{item_id}
    API->>Store: load refined/{id}.json, mutate item
    API->>Store: write refined/{id}.json
    API-->>Client: {status: ok, item_id, action}

    Client->>API: POST /episodes/{id}/commit
    API->>Store: append mg/memory_graph.jsonl
    API->>Store: append drift/drift.jsonl
    API-->>Client: {status: committed, episode_id}
```

## Status Code Summary

```mermaid
graph LR
    OK[200 OK] --> A[All successful responses]
    UE[422 Unprocessable] --> B[POST /events — bad payload schema]
    NF[404 Not Found] --> C[episode_id or item_id missing]
    BR[400 Bad Request] --> D[POST /commit — episode not yet refined]

    style OK fill:#0f3460,stroke:#533483,color:#fff
    style UE fill:#e94560,stroke:#fff,color:#fff
    style NF fill:#e94560,stroke:#fff,color:#fff
    style BR fill:#e94560,stroke:#fff,color:#fff
```
