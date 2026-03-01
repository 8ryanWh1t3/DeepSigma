# EDGE System

Exportable Decision Governance Engine: 11 standalone HTML modules with embedded ABP enforcement, gate verification, and delegation review triggers.

## EDGE Module Map

```mermaid
graph TD
    subgraph EDGE["EDGE Modules"]
        direction LR
        UNI["Unified v1.0.0\n8 tabs: Suite, Hiring, Bid,\nCompliance, BOE, IRIS,\nDelegation, Utility"]
        COH["Coherence Dashboard v2.0.0\n4 tabs: Overview, Claims,\nDrift, Analysis"]
        JRM["JRM EDGE v1.0.7\n6 tabs: Run, Events, Packets,\nHealth, Test Lab, Replay"]
        RFP["RFP Co-Pilot v1.0.0\n8 tabs: Overview, Quick Start,\nPrompt, JSON, Power Query,\nShare, Roles, Troubleshooting"]
        RFPX["RFP Exec Brief v1.0.0\n1-page summary + Print/PDF"]

        HIR["Hiring UI v1.0.0\nStaffing intake"]
        BID["BidNoBid UI v1.0.0\nOpportunity evaluation"]
        CMP["Compliance Matrix v1.0.0\nRequirements mapping"]
        BOE["BOE Pricing v1.0.0\nRate calculations"]
        AWD["Award Staffing v1.2.0\nCost estimation"]
        SRO["Suite ReadOnly v1.0.0\nTelemetry + rollup"]
    end

    ABP["ABP v1\nABP-bf0afe15\nsha256:c01f..."]

    ABP -->|"embedded in"| UNI
    ABP -->|"embedded in"| COH
    ABP -->|"embedded in"| HIR
    ABP -->|"embedded in"| BID
    ABP -->|"embedded in"| CMP
    ABP -->|"embedded in"| BOE
    ABP -->|"embedded in"| AWD
    ABP -->|"embedded in"| SRO

    style EDGE fill:#e8f5e9,stroke:#43a047
    style ABP fill:#fff3bf,stroke:#f59f00
    style JRM fill:#e3f2fd,stroke:#1e88e5
    style RFP fill:#fff3e0,stroke:#fb8c00
    style RFPX fill:#fff3e0,stroke:#fb8c00
```

## JRM EDGE Pipeline (v1.0.7)

```mermaid
graph LR
    subgraph Input["Log Sources"]
        EVE["Suricata EVE"]
        SNR["Snort fast.log"]
        CPL["Copilot JSONL"]
    end

    subgraph Pipeline["9-Stage Seeded Pipeline"]
        direction LR
        S1["RAW"] --> S2["PARSE"] --> S3["NORMALIZE"] --> S4["JOIN"]
        S4 --> S5["TRUTH"] --> S6["REASONING"] --> S7["DRIFT"]
        S7 --> S8["PATCH"] --> S9["MEMORY"]
    end

    subgraph Features["v1.0.7 Features"]
        SW["So What Panel\nper-stage what/why/next"]
        AZ["Analyzer ↔ Deep Sigma\nview toggle"]
        TL["Packet Timeline\nchain + diff"]
        ST["Stream Mode\nFreeze + Seal"]
        PD["Policy Drawer\nlocked thresholds\nregression rerun"]
    end

    EVE & SNR & CPL --> S1
    S9 --> SW
    S9 --> AZ
    S9 --> TL
    S9 --> ST
    S9 --> PD

    style Input fill:#e3f2fd,stroke:#1e88e5
    style Pipeline fill:#e8f5e9,stroke:#43a047
    style Features fill:#fff3e0,stroke:#fb8c00
```

## RFP Co-Pilot Workflow

```mermaid
flowchart LR
    RFP["RFP Document"] --> PROMPT["AI Extraction\nCo-Pilot Prompt"]
    PROMPT --> JSON["rfp_extract.json\nStructured Output"]
    JSON --> PQ["Excel Power Query\n6 M Scripts"]
    PQ --> TABLES["Live Tables\nSolicitation | Dates\nAttachments | Amendments\nRisks | Open Items"]
    TABLES --> ROLES["Team Role Pull\n6 Roles"]

    AMD["Amendment"] -.->|"rerun"| PROMPT
    PQ -.->|"Ctrl+Alt+F5\nRefresh All"| TABLES

    style RFP fill:#e3f2fd,stroke:#1e88e5
    style PROMPT fill:#fff3bf,stroke:#f59f00
    style JSON fill:#e0f2f1,stroke:#26a69a
    style PQ fill:#f3e5f5,stroke:#8e24aa
    style TABLES fill:#e8f5e9,stroke:#43a047
    style ROLES fill:#fce4ec,stroke:#e53935
    style AMD fill:#fff3e0,stroke:#fb8c00
```

## ABP Gate Enforcement Flow

```mermaid
flowchart TD
    subgraph Input["EDGE HTML Export"]
        HTML["EDGE_*.html\n(8 files)"]
    end

    subgraph Gate["gate_abp.py"]
        C1["1. ABP Present\nscript id=ds-abp-v1"]
        C2["2. JSON Valid"]
        C3["3. Hash Integrity\nsha256 canonical"]
        C4["4. ID Deterministic\nscope+auth+created"]
        C5["5. No Contradictions\nallow vs deny"]
        C6["6. Ref Match\n(if --abp-ref)"]
        C7["7. Module in Scope\nfilename to module"]
        C8["8. Status Bar\nabpStatusBar div"]
        C9["9. Verification JS\nabpSelfVerify"]
        C10["10. Delegation Review\n(optional)"]
    end

    HTML --> C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> C8 --> C9 --> C10

    C10 -->|"10/10 pass"| PASS["GATE PASS\n80/80 across 8 files"]
    C10 -->|"any fail"| FAIL["GATE FAIL\nBlocked from distribution"]

    style Input fill:#e3f2fd,stroke:#1e88e5
    style Gate fill:#fff3e0,stroke:#fb8c00
    style PASS fill:#51cf66,color:#fff
    style FAIL fill:#ff6b6b,color:#fff
```

## Delegation Review Closed Loop

```mermaid
flowchart LR
    subgraph Delegate["1. Delegate"]
        BOARD["Board\nLeadership"]
        ABP["ABP v1\nBoundaries"]
        BOARD -->|"defines"| ABP
    end

    subgraph Execute["2. Execute"]
        AGENT["AI Agents"]
        VALIDATORS["Runtime\nValidators"]
        SEALED["Sealed Runs"]
        ABP -->|"governs"| AGENT
        AGENT --> VALIDATORS --> SEALED
    end

    subgraph Reassess["3. Reassess"]
        DRIFT["Drift Signals"]
        DRT["DRT Triggers"]
        REVIEW["Delegation\nReview"]
        SEALED -->|"produce"| DRIFT
        DRIFT -->|"filter"| DRT
        DRT -->|"threshold"| REVIEW
    end

    REVIEW -->|"abp_patch"| ABP

    style Delegate fill:#e7f5ff,stroke:#1c7ed6
    style Execute fill:#fff3bf,stroke:#f59f00
    style Reassess fill:#fce4ec,stroke:#e53935
```

## Delegation Review Triggers

```mermaid
flowchart TD
    DS["Drift Events\nfunctional | data | assumption\npolicy | authority | coherence"]

    DS --> E1["DRT-001\nRecurring fingerprint\n>= 3 in 14d"]
    DS --> E2["DRT-002\nIrreversible blocked\n>= 5 in 7d"]
    DS --> E3["DRT-003\nCoherence < 60\n3 consecutive runs"]
    DS --> E4["DRT-004\nExpired claims\n>= 4 in 30d"]

    E1 -->|"warn, auto"| OPEN["Open Review"]
    E2 -->|"critical, auto"| OPEN
    E3 -->|"critical, auto"| OPEN
    E4 -->|"warn, manual"| QUEUE["Queue"]

    OPEN --> REVIEWER["Reviewer\nthreshold: 1\ntimeout: 7d"]
    QUEUE --> REVIEWER

    REVIEWER --> PATCH["abp_patch"]
    REVIEWER --> REPLACE["abp_replace"]
    REVIEWER --> REVOKE["abp_revoke"]

    PATCH --> REBUILD["Rebuild ABP\nRe-stamp EDGE\nRe-gate"]

    style DS fill:#e3f2fd,stroke:#1e88e5
    style OPEN fill:#fff3bf,stroke:#f59f00
    style QUEUE fill:#fff3bf,stroke:#f59f00
    style PATCH fill:#d3f9d8,stroke:#37b24d
    style REPLACE fill:#e7f5ff,stroke:#1c7ed6
    style REVOKE fill:#ff6b6b,color:#fff
```

## Unified Tab Architecture

```mermaid
graph TD
    subgraph Unified["EDGE Unified v1.0.0"]
        direction LR
        subgraph IFrameTabs["iframe Modules"]
            T1["Suite"]
            T2["Hiring"]
            T3["Bid"]
            T4["Compliance"]
            T5["BOE"]
        end

        subgraph HostPanels["Host-Level Panels"]
            T6["IRIS\nQuery resolution"]
            T7["Delegation\nTrigger board"]
            T8["Utility\nMeta + testing"]
        end
    end

    subgraph Context["ABP Context Bar"]
        CTX["Tab-specific governance\nObjectives, tools,\npermissions per module"]
    end

    T1 & T2 & T3 & T4 & T5 -.->|"Blob URL\nlazy load"| IFRAME["iframe element"]
    T6 & T7 & T8 -.->|"direct DOM\nlocalStorage access"| PANE["host pane div"]

    IFrameTabs --> CTX
    HostPanels --> CTX

    style Unified fill:#e8f5e9,stroke:#43a047
    style IFrameTabs fill:#fff3bf,stroke:#f59f00
    style HostPanels fill:#e7f5ff,stroke:#1c7ed6
    style Context fill:#fce4ec,stroke:#e53935
```

## End-to-End EDGE Export Pipeline

```mermaid
flowchart TD
    subgraph Build["Build Phase"]
        SCOPE["Define Scope\ncontract + program + modules"]
        AUTH["Authority Ledger\nactive entry"]
        CONFIG["ABP Config\nobjectives, tools, data,\napprovals, escalation,\nruntime, proof, delegation"]
        SCOPE & AUTH & CONFIG --> BUILDER["build_abp.py"]
        BUILDER --> ABP_FILE["abp_v1.json"]
    end

    subgraph Stamp["Stamp Phase"]
        ABP_FILE --> STAMP["Re-stamp Script"]
        STAMP --> H1["Unified.html"]
        STAMP --> H2["Hiring.html"]
        STAMP --> H3["BidNoBid.html"]
        STAMP --> H4["Compliance.html"]
        STAMP --> H5["BOE.html"]
        STAMP --> H6["AwardStaffing.html"]
        STAMP --> H7["Coherence.html"]
        STAMP --> H8["SuiteRO.html"]
    end

    subgraph Verify["Verify Phase"]
        H1 & H2 & H3 & H4 & H5 & H6 & H7 & H8 --> GATE["gate_abp.py\n80 checks"]
        ABP_FILE --> VABP["verify_abp.py\n8 checks"]
        ABP_FILE --> VPACK["verify_pack.py\n--require-abp"]
    end

    subgraph Distribute["Distribute"]
        GATE -->|"ALL PASS"| DIST["Ship EDGE exports"]
        GATE -->|"ANY FAIL"| BLOCK["Blocked"]
    end

    style Build fill:#e7f5ff,stroke:#1c7ed6
    style Stamp fill:#fff3bf,stroke:#f59f00
    style Verify fill:#e8f5e9,stroke:#43a047
    style DIST fill:#51cf66,color:#fff
    style BLOCK fill:#ff6b6b,color:#fff
```
