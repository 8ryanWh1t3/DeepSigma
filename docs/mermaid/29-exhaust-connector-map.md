# Exhaust Connector Map

How the three adapter types normalise raw AI interaction logs into EpisodeEvents and deliver them to the Exhaust Inbox.

```mermaid
graph LR
    subgraph Sources["Source Systems"]
        APP[LangChain App<br/>in-process callbacks]
        AZL[Azure OpenAI<br/>JSONL log files]
        ANL[Anthropic Messages API<br/>JSONL log files]
        RAW[Any Agent<br/>raw REST calls]
    end

    subgraph Adapters["Adapters — adapters/"]
        APP -->|inherits BaseCallbackHandler| LC["langchain_exhaust.py<br/>─────────────────<br/>on_llm_start → prompt event<br/>on_llm_end → completion + metric<br/>• latency_ms (monotonic delta)<br/>• model name from serialized<br/>on_tool_start/end → tool events"]
        AZL -->|reads JSONL| AZA["azure_openai_exhaust.py<br/>─────────────────<br/>_normalise_entry()<br/>messages[] → prompt events<br/>choices[] → completion events<br/>usage{} → metric event"]
        ANL -->|reads JSONL| ANA["anthropic_exhaust.py<br/>─────────────────<br/>_normalise_entry()<br/>input messages[] → prompt events<br/>content[] text → completion event<br/>content[] tool_use → tool event<br/>usage{} → metric event"]
        RAW -->|POST JSON| MAN[Manual / SDK<br/>direct API calls]
    end

    subgraph Normalise["Normalised Shape — EpisodeEvent"]
        LC --> EE["event_id, episode_id, event_type<br/>timestamp, source, user_hash<br/>session_id, project, team<br/>payload: Dict"]
        AZA --> EE
        ANA --> EE
        MAN --> EE
    end

    subgraph Delivery["Delivery"]
        EE -->|POST /api/exhaust/events| API["Exhaust Inbox API<br/>:8000"]
        EE -->|--dry-run flag| DRY[Dry-run print<br/>no network call]
    end

    subgraph Grouping["Session Grouping — _group_events()"]
        API --> GRP[Bucket by<br/>session_id + time window]
        GRP --> EP[DecisionEpisode<br/>ready to assemble]
    end

    style Sources fill:#1a1a2e,stroke:#e94560,color:#fff
    style Adapters fill:#16213e,stroke:#0f3460,color:#fff
    style Normalise fill:#162447,stroke:#533483,color:#fff
    style Delivery fill:#0f3460,stroke:#e94560,color:#fff
    style Grouping fill:#1a1a2e,stroke:#533483,color:#fff
```

## Source Enum — Adapter Identity

Each adapter stamps a `source` field so downstream analysis can distinguish origin.

```mermaid
graph TD
    SRC[Source enum] --> LC2[langchain]
    SRC --> OA[openai]
    SRC --> AZ2[azure]
    SRC --> AN2[anthropic]
    SRC --> MN2[manual]

    LC2 -.->|set by| LCA[langchain_exhaust.py]
    AZ2 -.->|set by| AZB[azure_openai_exhaust.py]
    AN2 -.->|set by| ANB[anthropic_exhaust.py]
    MN2 -.->|set by| MNAPI[Direct REST callers<br/>cookbook / tests]

    style SRC fill:#e94560,stroke:#fff,color:#fff
```

## Metric Enrichment — LangChain Adapter (Build 29)

Targeted additions to `langchain_exhaust.py` that add observability fields to every LLM call.

```mermaid
flowchart LR
    START["on_llm_start(serialized, run_id)"] --> ST["_run_start[run_id] = time.monotonic()"]
    START --> MN3["_run_model[run_id] = serialized\n.kwargs.model_name"]

    END["on_llm_end(response, run_id)"] --> LAT["latency_ms =\n(monotonic() − _run_start.pop()) × 1000"]
    END --> MOD["model = _run_model.pop(run_id)"]
    LAT --> EMIT["emit metric event\npayload = {latency_ms, model}"]
    MOD --> EMIT

    style START fill:#16213e,stroke:#0f3460,color:#fff
    style END fill:#16213e,stroke:#0f3460,color:#fff
    style EMIT fill:#0f3460,stroke:#533483,color:#fff
```
