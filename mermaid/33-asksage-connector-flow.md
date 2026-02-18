# AskSage Connector Flow

Data flow from AskSage API through the exhaust adapter into canonical records, including the two-phase auth token lifecycle.

```mermaid
flowchart TB
    subgraph AskSage["AskSage API"]
        AUTH_EP[/auth/token<br/>API Key → 24h Bearer/]
        QUERY_EP[/query<br/>POST prompt + model/]
        TRAIN_EP[/train<br/>POST dataset + config/]
        DS_EP[/datasets<br/>GET list · POST upload/]
        HIST_EP[/history<br/>GET past queries/]
    end

    subgraph Connector["AskSage Connector"]
        CLIENT[AskSageClient]
        TOKEN[Token Manager<br/>auto-refresh < 24h]
        DTE_CHECK[DTE Gate<br/>budget · TTL · scope]
        EXHAUST_AD[Exhaust Adapter<br/>source = asksage]
    end

    subgraph RAL["Σ OVERWATCH"]
        EPISODE[EpisodeEvent]
        CANONICAL[Canonical Record]
        INBOX[Exhaust Inbox]
    end

    subgraph MCP["MCP Tools"]
        T1[asksage.query]
        T2[asksage.models]
        T3[asksage.datasets]
        T4[asksage.history]
    end

    %% Auth flow
    CLIENT -->|API Key| AUTH_EP
    AUTH_EP -->|24h token| TOKEN
    TOKEN -->|bearer| CLIENT

    %% API calls
    CLIENT -->|prompt| QUERY_EP
    CLIENT -->|config| TRAIN_EP
    CLIENT -->|list/upload| DS_EP
    CLIENT -->|fetch| HIST_EP

    %% DTE gating
    T1 --> DTE_CHECK
    T2 --> DTE_CHECK
    T3 --> DTE_CHECK
    T4 --> DTE_CHECK
    DTE_CHECK -->|approved| CLIENT

    %% Exhaust path
    QUERY_EP -->|response| EXHAUST_AD
    TRAIN_EP -->|job status| EXHAUST_AD
    DS_EP -->|result| EXHAUST_AD
    HIST_EP -->|records| EXHAUST_AD

    EXHAUST_AD --> EPISODE
    EPISODE --> CANONICAL
    CANONICAL --> INBOX

    style AskSage fill:#1a73e8,stroke:#1a73e8,color:#fff
    style Connector fill:#16213e,stroke:#0f3460,color:#fff
    style RAL fill:#e94560,stroke:#e94560,color:#fff
    style MCP fill:#162447,stroke:#1f4068,color:#fff
```

## Key Details

- **Two-phase auth**: Long-lived API key exchanges for a 24-hour bearer token. Token Manager auto-refreshes before expiry.
- **DTE Gate**: Every MCP tool call passes through DTE constraint checking before the API request is issued.
- **Exhaust Adapter**: Captures `model`, `prompt_hash`, `token_count`, `latency_ms`, `cost_usd` per operation.
- **Canonical Records**: All exhaust events are wrapped in the standard canonical envelope with provenance metadata.
