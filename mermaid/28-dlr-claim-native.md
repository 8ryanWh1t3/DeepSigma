# 28 — DLR Claim-Native Architecture

The Decision Log Record refactored as a claim graph — five decision stages, rationale edges, and freshness snapshots.

## DLR Decision Flow (Claim Stages)

```mermaid
flowchart LR
    subgraph Context["1. CONTEXT"]
        C1["CLAIM-0001<br/>observation<br/>🟢 0.94<br/><i>trigger</i>"]
        C0["CLAIM-0000<br/>observation<br/>🟢 0.99<br/><i>baseline</i>"]
    end

    subgraph Rationale["2. RATIONALE"]
        C2["CLAIM-0002<br/>inference<br/>🟢 0.88<br/><i>risk assessment</i>"]
        C3["CLAIM-0003<br/>assumption<br/>🟡 0.75<br/><i>threat model</i>"]
    end

    subgraph Action["3. ACTION"]
        C10["CLAIM-0010<br/>norm<br/>🟢 1.00<br/><i>policy mandate</i>"]
        C11["CLAIM-0011<br/>constraint<br/>🟢 1.00<br/><i>regulatory</i>"]
    end

    subgraph Verify["4. VERIFICATION"]
        C20["CLAIM-0020<br/>observation<br/>🟢 0.92<br/><i>post-action check</i>"]
    end

    subgraph Outcome["5. OUTCOME"]
        C30["CLAIM-0030<br/>observation<br/>🟢 0.95<br/><i>result confirmed</i>"]
    end

    Context --> Rationale --> Action --> Verify --> Outcome

    style Context fill:#0f3460,stroke:#e94560,stroke-width:2px
    style Rationale fill:#533483,stroke:#e94560,stroke-width:2px
    style Action fill:#1a1a2e,stroke:#e94560,stroke-width:2px
    style Verify fill:#2b2d42,stroke:#e94560,stroke-width:2px
    style Outcome fill:#16213e,stroke:#2ecc71,stroke-width:2px
```

## Rationale Graph (Weighted Edges)

```mermaid
graph TD
    C0["CLAIM-0000<br/>baseline<br/>🟢 0.99"] -->|"supports<br/>w: 0.99"| C1["CLAIM-0001<br/>trigger<br/>🟢 0.94"]
    C1 -->|"informs<br/>w: 0.94"| C2["CLAIM-0002<br/>risk<br/>🟢 0.88"]
    C3["CLAIM-0003<br/>threat<br/>🟡 0.75"] -->|"justifies<br/>w: 0.75"| C10["CLAIM-0010<br/>policy<br/>🟢 1.00"]
    C2 -->|"justifies<br/>w: 0.88"| C10
    C11["CLAIM-0011<br/>regulatory<br/>🟢 1.00"] -->|"supports<br/>w: 1.00"| C10
    C20["CLAIM-0020<br/>verified<br/>🟢 0.92"] -->|"verifies<br/>w: 0.92"| C30["CLAIM-0030<br/>outcome<br/>🟢 0.95"]

    ROOT(("rootClaim")):::root --> C1

    style C0 fill:#16213e,stroke:#2ecc71
    style C1 fill:#16213e,stroke:#2ecc71,stroke-width:3px
    style C2 fill:#16213e,stroke:#2ecc71
    style C3 fill:#16213e,stroke:#f39c12
    style C10 fill:#533483,stroke:#2ecc71,stroke-width:2px
    style C11 fill:#533483,stroke:#2ecc71
    style C20 fill:#2b2d42,stroke:#2ecc71
    style C30 fill:#0f3460,stroke:#2ecc71,stroke-width:2px
    classDef root fill:#e94560,stroke:#e94560,color:#fff
```

## DLR vs Episode: Before and After

```mermaid
graph LR
    subgraph Before["Episode-Centric DLR (old)"]
        direction TB
        EP1["episodeId"]
        DTE1["dteRef"]
        AC1["action_contract<br/><i>flat fields</i>"]
        VER1["verification<br/><i>result only</i>"]
        POL1["policy_stamp<br/><i>present/absent</i>"]
        OUT1["outcome_code<br/><i>string</i>"]
    end

    subgraph After["Claim-Native DLR (new)"]
        direction TB
        EP2["episodeId"]
        CL["claims<br/><i>context · rationale · action<br/>verification · outcome</i>"]
        RG["rationaleGraph<br/><i>typed + weighted edges</i>"]
        FS["freshnessSnapshot<br/><i>allFresh? · expired[] · stalest</i>"]
        PS["policyStamp<br/><i>+ result enum</i>"]
        CS["coherenceScore<br/><i>0–100</i>"]
        SEAL["seal<br/><i>hash + version + patchLog</i>"]
    end

    Before -.->|"refactored to"| After

    style Before fill:#2b2d42,stroke:#e74c3c,stroke-dasharray: 5 5
    style After fill:#1a1a2e,stroke:#2ecc71,stroke-width:2px
    style CL fill:#533483,stroke:#e94560
    style RG fill:#533483,stroke:#e94560
    style FS fill:#0f3460,stroke:#e94560
```

## claimRef Snapshot Model

```mermaid
erDiagram
    DLR ||--o{ CLAIM_REF : "contains"
    CLAIM_REF ||--|| CLAIM : "references"

    DLR {
        string dlrId PK
        string episodeId
        string decisionType
        datetime recordedAt
        object rationaleGraph
        object freshnessSnapshot
        number coherenceScore
        object seal
    }

    CLAIM_REF {
        string claimId FK
        string truthType
        number confidenceAtDecision
        string statusLightAtDecision
        boolean wasFresh
        string role
        string stage
    }

    CLAIM {
        string claimId PK
        string statement
        object scope
        string truthType
        number confidence
        string statusLight
        object halfLife
        object graph
        object seal
    }
```

## Composability: Everything is Claims

```mermaid
graph TB
    CLAIM["Claim Primitive<br/><i>atomic truth unit</i>"]

    DLR["DLR<br/><i>claim subgraph<br/>+ rationale edges</i>"]
    CANON["Canon<br/><i>blessed claimIds<br/>→ long-term memory</i>"]
    DRIFT["Drift<br/><i>confidence decay<br/>contradiction · expiry</i>"]
    RETCON["Retcon<br/><i>supersede claim<br/>preserve original</i>"]
    PATCH["Patch<br/><i>seal.patchLog<br/>append-only</i>"]
    IRIS["IRIS<br/><i>graph walk<br/>WHY · WHAT_CHANGED</i>"]

    CLAIM --> DLR
    CLAIM --> CANON
    CLAIM --> DRIFT
    CLAIM --> RETCON
    CLAIM --> PATCH
    CLAIM --> IRIS

    DLR --> IRIS
    DRIFT --> RETCON
    RETCON --> PATCH

    style CLAIM fill:#e94560,stroke:#e94560,color:#fff,stroke-width:3px
    style DLR fill:#533483,stroke:#e94560
    style CANON fill:#0f3460,stroke:#e94560
    style DRIFT fill:#2b2d42,stroke:#f39c12
    style RETCON fill:#2b2d42,stroke:#e94560
    style PATCH fill:#16213e,stroke:#e94560
    style IRIS fill:#16213e,stroke:#2ecc71
```
