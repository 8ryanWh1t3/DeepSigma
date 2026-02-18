# SharePoint Connector Flow

Data extraction from SharePoint Online via Microsoft Graph API, with delta sync and webhook-driven incremental updates.

```mermaid
flowchart TB
    subgraph SharePoint["SharePoint Online"]
        SP_LIST[Lists / Libraries]
        SP_WEBHOOK[Webhook Subscription]
        SP_DELTA[Delta API<br/>GET /delta]
    end

    subgraph Connector["SharePoint Connector"]
        AUTH[Graph Auth<br/>OAuth App Registration]
        FETCH[Fetch Records<br/>GET /items]
        DELTA_SYNC[Delta Sync Loop<br/>deltaLink cursor]
        WEBHOOK_RX[Webhook Receiver<br/>POST /webhook/sharepoint]
        FIELD_MAP[Field Mapping<br/>SP columns → canonical fields]
        VALIDATE[Validation Gate<br/>QR rules + schema check]
    end

    subgraph RAL["Σ OVERWATCH"]
        CANONICAL[Canonical Record<br/>envelope + provenance]
        INGEST[Ingest Pipeline]
        EXHAUST[Exhaust Inbox]
    end

    SP_LIST -->|initial full pull| FETCH
    SP_DELTA -->|incremental changes| DELTA_SYNC
    SP_WEBHOOK -->|change notification| WEBHOOK_RX

    AUTH -->|bearer token| FETCH
    AUTH -->|bearer token| DELTA_SYNC

    FETCH --> FIELD_MAP
    DELTA_SYNC --> FIELD_MAP
    WEBHOOK_RX -->|trigger| DELTA_SYNC

    FIELD_MAP --> VALIDATE

    VALIDATE -->|pass| CANONICAL
    VALIDATE -->|fail| REJECT[Reject + Log]
    REJECT --> EXHAUST

    CANONICAL --> INGEST
    INGEST --> EXHAUST

    DELTA_SYNC -->|save deltaLink| DELTA_SYNC

    style SharePoint fill:#0078d4,stroke:#0078d4,color:#fff
    style Connector fill:#16213e,stroke:#0f3460,color:#fff
    style RAL fill:#e94560,stroke:#e94560,color:#fff
```

## Key Details

- **Delta Sync Loop**: Uses Microsoft Graph `/delta` endpoint with a persisted `deltaLink` cursor. Only changed items are fetched on subsequent runs.
- **Webhook Subscription**: Registered via Graph API; SharePoint sends change notifications to the connector's webhook endpoint, triggering an immediate delta sync.
- **Validation Gate**: Applies QR rules (schema, required fields, data types) before admitting records into the canonical store.
- **Rejected records** are logged to the Exhaust Inbox with failure reasons for audit.
