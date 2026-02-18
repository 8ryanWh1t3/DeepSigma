# Snowflake Connector Flow

Dual-mode connector: Cortex AI (LLM completions + embeddings) and warehouse SQL (query + sync), sharing a unified auth layer.

```mermaid
flowchart TB
    subgraph Auth["Shared Auth Layer"]
        JWT[JWT Keypair]
        OAUTH[OAuth]
        PAT[Personal Access Token]
        AUTH_MUX{Auth Mux}
        JWT --> AUTH_MUX
        OAUTH --> AUTH_MUX
        PAT --> AUTH_MUX
    end

    subgraph CortexMode["Cortex AI Mode"]
        CORTEX_API[Cortex REST API<br/>/api/v2/cortex]
        COMPLETE[cortex.complete<br/>LLM completion]
        EMBED[cortex.embed<br/>embedding generation]
    end

    subgraph WarehouseMode["Warehouse SQL Mode"]
        SQL_API[SQL REST API<br/>/api/v2/statements]
        QUERY[snowflake.query<br/>execute SQL]
        TABLES[snowflake.tables<br/>list tables/views]
        SYNC[snowflake.sync<br/>incremental merge]
    end

    subgraph Connector["Snowflake Connector"]
        DTE_CHECK[DTE Gate<br/>budget · TTL · scope]
        EXHAUST_AD[Exhaust Adapter<br/>source = snowflake]
    end

    subgraph RAL["Σ OVERWATCH"]
        EPISODE[EpisodeEvent]
        CANONICAL[Canonical Record]
        INBOX[Exhaust Inbox]
    end

    %% Auth
    AUTH_MUX -->|token| CORTEX_API
    AUTH_MUX -->|token| SQL_API

    %% Cortex path
    COMPLETE --> DTE_CHECK
    EMBED --> DTE_CHECK
    DTE_CHECK -->|approved| CORTEX_API
    CORTEX_API -->|response| EXHAUST_AD

    %% Warehouse path
    QUERY --> DTE_CHECK
    TABLES --> DTE_CHECK
    SYNC --> DTE_CHECK
    DTE_CHECK -->|approved| SQL_API
    SQL_API -->|rows| EXHAUST_AD

    %% Exhaust
    EXHAUST_AD --> EPISODE
    EPISODE --> CANONICAL
    CANONICAL --> INBOX

    %% Sync watermark
    SYNC -.->|_updated_at cursor| SYNC

    style Auth fill:#29b5e8,stroke:#29b5e8,color:#fff
    style CortexMode fill:#0f3460,stroke:#533483,color:#fff
    style WarehouseMode fill:#0f3460,stroke:#533483,color:#fff
    style Connector fill:#16213e,stroke:#0f3460,color:#fff
    style RAL fill:#e94560,stroke:#e94560,color:#fff
```

## Key Details

- **Shared Auth Layer**: All three auth methods (JWT keypair, OAuth, PAT) funnel through a single mux. The connector selects the method based on config.
- **Cortex AI Mode**: REST calls to `/api/v2/cortex` for `complete` and `embed`. DTE-gated on token budget and model allowlist.
- **Warehouse SQL Mode**: REST calls to `/api/v2/statements` for arbitrary SQL. `sync` uses an `_updated_at` watermark column for incremental merge.
- **Exhaust Adapter**: Captures `mode` (cortex/warehouse), `operation`, `latency_ms`, `rows_affected`, `token_count`, `cost_usd`.
