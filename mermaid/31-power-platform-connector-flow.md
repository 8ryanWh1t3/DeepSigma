# Power Platform Connector Flow

Data flow between Power Platform (Dataverse, Power Automate) and the RAL canonical store.

```mermaid
flowchart TB
    subgraph PowerPlatform["Power Platform"]
        DV[Dataverse<br/>Web API]
        PA[Power Automate<br/>Flow Trigger]
        CC[Custom Connector<br/>RAL → Dataverse]
    end

    subgraph Connector["Power Platform Connector"]
        AUTH[OAuth / App Registration]
        DV_FETCH[Fetch Entities<br/>GET /api/data/v9.2]
        DV_MAP[Field Mapping<br/>Dataverse → canonical]
        PA_WEBHOOK[Webhook Receiver<br/>POST /webhook/power-automate]
        PA_TRANSFORM[Auto-Transform<br/>Flow output → canonical]
        CC_REVERSE[Reverse Sync<br/>canonical → Dataverse entity]
        VALIDATE[Validation Gate]
    end

    subgraph RAL["Σ OVERWATCH"]
        CANONICAL[Canonical Record]
        INGEST[Ingest Pipeline]
        EXHAUST[Exhaust Inbox]
    end

    %% Dataverse inbound
    DV -->|entity query| DV_FETCH
    AUTH -->|bearer token| DV_FETCH
    DV_FETCH --> DV_MAP
    DV_MAP --> VALIDATE

    %% Power Automate inbound
    PA -->|trigger payload| PA_WEBHOOK
    PA_WEBHOOK --> PA_TRANSFORM
    PA_TRANSFORM --> VALIDATE

    %% Validation
    VALIDATE -->|pass| CANONICAL
    VALIDATE -->|fail| REJECT[Reject + Log]
    REJECT --> EXHAUST

    CANONICAL --> INGEST
    INGEST --> EXHAUST

    %% Reverse flow
    CANONICAL -->|outbound sync| CC_REVERSE
    CC_REVERSE -->|PATCH /api/data/v9.2| DV
    AUTH -->|bearer token| CC_REVERSE

    %% Custom connector registration
    CC -.->|registered in| DV

    style PowerPlatform fill:#742774,stroke:#742774,color:#fff
    style Connector fill:#16213e,stroke:#0f3460,color:#fff
    style RAL fill:#e94560,stroke:#e94560,color:#fff
```

## Key Details

- **Dataverse Web API**: Standard OData v4 endpoint for CRUD on entities. The connector maps Dataverse entity fields to canonical record fields.
- **Power Automate Trigger**: Flows can POST payloads to the connector's webhook, enabling event-driven ingestion (e.g., on record create/update).
- **Custom Connector (Reverse Flow)**: A Power Platform custom connector allows Dataverse and Power Apps to call back into RAL, writing canonical records into Dataverse entities.
- **Validation Gate**: Same QR rule engine as all other connectors.
