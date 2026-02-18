# Exhaust Inbox Pipeline

Full architecture of the Exhaust Inbox — from adapter emission through bucket extraction to Coherence Ops.

```mermaid
graph TB
    subgraph Adapters["Adapters (Build 29)"]
        LC[LangChain Callback<br/>on_llm_start / on_llm_end]
        AZ[Azure OpenAI Adapter<br/>Batch JSONL]
        AN[Anthropic Adapter<br/>Messages API JSONL]
        MN[Manual / REST<br/>POST /api/exhaust/events]
    end

    subgraph Inbox["Exhaust Inbox API"]
        EVT[Event Store<br/>events.jsonl]
        LC -->|POST /events| EVT
        AZ -->|POST /events| EVT
        AN -->|POST /events| EVT
        MN --> EVT
        EVT --> ASM[Episode Assembler<br/>group by session_id]
        ASM --> EP[Episode Store<br/>episodes/{id}.json]
    end

    subgraph Refiner["Refiner — POST /episodes/{id}/refine"]
        EP --> RF{EXHAUST_USE_LLM?}
        RF -->|"= 1 + ANTHROPIC_API_KEY set"| LLM[LLM Extraction<br/>claude-haiku-4-5-20251001]
        RF -->|"= 0 (default)"| RB[Rule-Based Extraction<br/>keyword + pattern matching]
        LLM -->|fallback on any error| RB
        LLM --> BKT
        RB --> BKT
        BKT[Buckets<br/>TRUTH · REASONING · MEMORY]
        BKT --> DRIFT[Drift Detector<br/>contradiction / stale_reference /<br/>missing_policy / low_coverage]
        DRIFT --> SCORE[Coherence Scorer<br/>0–100 · Grade A–F]
        SCORE --> REF[Refined Episode<br/>refined/{id}.json]
    end

    subgraph Commit["POST /episodes/{id}/commit"]
        REF --> CMT[Commit Handler]
        CMT --> MG[Memory Graph<br/>mg/memory_graph.jsonl]
        CMT --> DRF[Drift Log<br/>drift/drift.jsonl]
        CMT --> COH[Coherence Ops<br/>DLR · RS · DS · MG]
    end

    style Adapters fill:#1a1a2e,stroke:#e94560,color:#fff
    style Inbox fill:#16213e,stroke:#0f3460,color:#fff
    style Refiner fill:#162447,stroke:#e94560,color:#fff
    style Commit fill:#0f3460,stroke:#533483,color:#fff
```

## Bucket Extraction Detail

How events are mapped into TRUTH, REASONING, and MEMORY items.

```mermaid
flowchart TD
    EV[Episode Events] --> ET{event_type}

    ET -->|metric| TM["TRUTH item<br/>claim = '{name} is {value}{unit}'<br/>confidence = 0.80"]
    ET -->|completion| TC["TRUTH items<br/>parse key sentences<br/>confidence = 0.70"]
    ET -->|completion| RC["REASONING items<br/>keyword scan: recommend / should /<br/>because / decided / consider<br/>confidence = 0.75"]
    ET -->|tool| MM["MEMORY item<br/>entity = tool name<br/>artifact_type = tool"]
    ET -->|any| ME["MEMORY item<br/>entity = episode_id<br/>artifact_type = episode<br/>(always emitted)"]

    TM --> CONF[Confidence<br/>clamped 0.0 – 1.0]
    TC --> CONF
    RC --> CONF
    MM --> CONF
    ME --> CONF

    CONF --> OUT["RefinedEpisode<br/>{truth, reasoning, memory,<br/>drift_signals, coherence_score, grade}"]

    style EV fill:#1a1a2e,stroke:#e94560,color:#fff
    style OUT fill:#0f3460,stroke:#533483,color:#fff
```

## Episode State Machine

```mermaid
stateDiagram-v2
    [*] --> Raw: POST /api/exhaust/events

    state Raw {
        [*] --> Buffered: appended to events.jsonl
        Buffered --> [*]
    }

    Raw --> Assembled: POST /api/exhaust/episodes/assemble\ngroup by session_id + project + team

    state Assembled {
        [*] --> Stored: episodes/{id}.json written
        Stored --> [*]
    }

    Assembled --> Refined: POST /api/exhaust/episodes/{id}/refine\nrule-based or LLM extraction

    state Refined {
        [*] --> Scored: coherence_score + grade computed
        Scored --> ItemReview: items accept / edit / reject via\nPATCH /api/exhaust/episodes/{id}/items/{item_id}
        ItemReview --> Scored: re-score on edit
        Scored --> [*]
    }

    Refined --> Committed: POST /api/exhaust/episodes/{id}/commit\nMG + Drift Log updated

    state Committed {
        [*] --> Sealed: episode_id recorded in memory graph
        Sealed --> [*]
    }

    Committed --> [*]
```
