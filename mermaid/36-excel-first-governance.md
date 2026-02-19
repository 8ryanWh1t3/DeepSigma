# Excel-First Governance

Architecture of the Creative Director Suite — how a shared Excel workbook becomes a governed decision surface via the BOOT protocol, named tables, and LLM-driven writeback.

```mermaid
flowchart TB
    subgraph Workbook["Excel Workbook (SharePoint)"]
        BOOT["BOOT!A1<br/>System Prompt"]
        subgraph Production["Production Data"]
            CLIENTS[Clients]
            CAMPAIGNS[Campaigns]
            PROJECTS[Projects]
            ASSETS[Assets]
            SHOTS[Shots]
            TASKS[Tasks]
            PROMPTS[Prompts]
            APPROVALS[Approvals]
        end
        subgraph Governance["Governance Tables"]
            TBL_TL[tblTimeline]
            TBL_DV[tblDeliverables]
            TBL_DLR[tblDLR]
            TBL_CL[tblClaims]
            TBL_AS[tblAssumptions]
            TBL_PL[tblPatchLog]
            TBL_CG[tblCanonGuardrails]
        end
        CI[CI_DASHBOARD<br/>Coherence Index]
    end

    subgraph LLM["LLM (ChatGPT / Claude / Copilot)"]
        INIT["Read BOOT!A1<br/>Initialize Context"]
        MENU["Menu Prompt<br/>What Would You Like To Do Today?"]
        subgraph Operations["7 Governed Operations"]
            OP1["1. Build Claims"]
            OP2["2. Refresh Assumptions"]
            OP3["3. Detect Drift"]
            OP4["4. Propose Patch"]
            OP5["5. Canon Audit"]
            OP6["6. Exec Summary"]
            OP7["7. Asset Checklist"]
        end
        OUTPUT["Output Contract<br/>Findings → Actions → Write-back Rows"]
    end

    subgraph Lenses["6-Lens Prompt Model"]
        L1[PRIME]
        L2[EXEC]
        L3[OPS]
        L4[AI-TECH]
        L5[HUMAN]
        L6[ICON]
    end

    %% BOOT initialization
    BOOT -->|attach workbook| INIT
    INIT --> MENU

    %% Menu to operations
    MENU --> Operations

    %% Operations read governance tables
    Operations -->|read tables<br/>cite TableName + Row_IDs| Governance
    Operations -->|read context| Production

    %% Lens filtering
    Lenses -->|filter perspective| Operations

    %% Output writeback
    Operations --> OUTPUT
    OUTPUT -->|paste write-back rows| Governance
    OUTPUT -->|update scores| CI

    %% Drift-Patch loop within workbook
    TBL_AS -->|expired TTL| OP3
    OP3 -->|drift detected| TBL_PL
    TBL_PL -->|patch applied| TBL_TL
    TBL_CG -->|enforce rules| OP5

    style Workbook fill:#0078d4,stroke:#0078d4,color:#fff
    style Production fill:#16213e,stroke:#0f3460,color:#fff
    style Governance fill:#162447,stroke:#e94560,color:#fff
    style LLM fill:#e94560,stroke:#e94560,color:#fff
    style Operations fill:#533483,stroke:#533483,color:#fff
    style Lenses fill:#0f3460,stroke:#0f3460,color:#fff
```

## Writeback Flow

```mermaid
sequenceDiagram
    participant U as User
    participant LLM as LLM (Claude / GPT / Copilot)
    participant WB as Excel Workbook

    U->>WB: Attach workbook to LLM
    WB->>LLM: BOOT!A1 (system prompt)
    LLM->>U: "What Would You Like To Do Today?"
    U->>LLM: "4 — Propose Patch Options"

    LLM->>WB: Read tblAssumptions, tblDLR, tblCanonGuardrails
    WB-->>LLM: Table data (25 rows each)

    LLM->>LLM: Detect expired assumptions (TTL < today)
    LLM->>LLM: Cross-reference Canon Guardrails
    LLM->>LLM: Generate Findings + Actions

    LLM->>U: Findings (3 expired assumptions)
    LLM->>U: Recommended Actions (2 patches)
    LLM->>U: Write-back rows for tblPatchLog

    U->>WB: Paste rows into tblPatchLog
    WB->>WB: CI_DASHBOARD recalculates
```

## Data Layer Summary

| Layer | Contents | Tables |
|-------|----------|--------|
| **Production** | 8 CSVs — creative production data (200 rows) | Clients, Campaigns, Projects, Assets, Shots, Tasks, Prompts, Approvals |
| **Governance** | 7 named tables — decision infrastructure (175 rows) | tblTimeline, tblDeliverables, tblDLR, tblClaims, tblAssumptions, tblPatchLog, tblCanonGuardrails |
| **Dashboard** | Coherence Index metrics | CI_DASHBOARD |

## Coherence Ops Mapping

| Excel Table | Primitive | Artifact |
|-------------|-----------|----------|
| tblTimeline, tblDeliverables | Decision Scaffold | DS |
| tblDLR | Decision Ledger Record | DLR |
| tblClaims | Atomic Claims | Claim |
| tblAssumptions | Reasoning Scaffold | RS |
| tblPatchLog | Patch Packets | Patch |
| tblCanonGuardrails | Canon | Canon |
