---
title: "Credibility Engine at Scale — Diagrams"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Diagrams — Production Scale

> Visual architecture for a 30,000–40,000 node Credibility Engine.

---

## Regional Architecture

```mermaid
graph TD
    subgraph East["Region East (12,000 nodes)"]
        E_HOT[Hot: 3,000] --> E_WARM[Warm: 6,000]
        E_WARM --> E_COLD[Cold: 3,000]
        E_SYNC[Sync Plane<br/>5 nodes, 2 beacons]
        E_DOMAINS[4 Decision<br/>Domains]
    end

    subgraph Central["Region Central (14,000 nodes)"]
        C_HOT[Hot: 4,000] --> C_WARM[Warm: 7,000]
        C_WARM --> C_COLD[Cold: 3,000]
        C_SYNC[Sync Plane<br/>5 nodes, 2 beacons]
        C_DOMAINS[5 Decision<br/>Domains]
    end

    subgraph West["Region West (10,000 nodes)"]
        W_HOT[Hot: 2,500] --> W_WARM[Warm: 5,000]
        W_WARM --> W_COLD[Cold: 2,500]
        W_SYNC[Sync Plane<br/>4 nodes, 2 beacons]
        W_DOMAINS[3 Decision<br/>Domains]
    end

    E_SYNC <-.->|federation| FED[Beacon<br/>Federation]
    C_SYNC <-.->|federation| FED
    W_SYNC <-.->|federation| FED

    FED --> CI[Credibility Index<br/>Composite: ~90]

    style East fill:#0f3460,stroke:#0f3460,color:#fff
    style Central fill:#16213e,stroke:#0f3460,color:#fff
    style West fill:#1a1a2e,stroke:#0f3460,color:#fff
```

---

## Evidence Temperature Flow

```mermaid
flowchart LR
    INGEST[Evidence<br/>Ingested] --> HOT[Hot Tier<br/>Active, <24h<br/>Sub-second access]
    HOT -->|age > 24h| WARM[Warm Tier<br/>Referenced <30d<br/>Seconds access]
    WARM -->|age > 30d| COLD[Cold Tier<br/>Sealed archive<br/>Minutes access]
    COLD -.->|never| DELETE[Never<br/>Deleted]

    HOT -->|TTL expires| DRIFT{Drift<br/>Signal}
    DRIFT -->|auto-patch| HOT
    DRIFT -->|escalate| DRI[Human<br/>DRI]

    style HOT fill:#c0392b,stroke:#c0392b,color:#fff
    style WARM fill:#f39c12,stroke:#f39c12,color:#fff
    style COLD fill:#2980b9,stroke:#2980b9,color:#fff
```

---

## Drift Triage at Scale

```mermaid
flowchart TD
    DETECT[Drift<br/>Detected] --> CLASSIFY{Severity?}

    CLASSIFY -->|Green| AUTO[Auto-Patch<br/>~90% of events]
    CLASSIFY -->|Yellow| REVIEW[DRI Review<br/>~8% of events]
    CLASSIFY -->|Red| ESCALATE[Escalation<br/>~2% of events]

    AUTO --> DS1[DS Artifact]
    REVIEW --> DS2[DS Artifact]
    ESCALATE --> DS3[DS Artifact]

    DS1 --> PATCH1[Auto-Patch]
    DS2 --> DRI_APPROVE{DRI<br/>Approves?}
    DS3 --> WAR[Senior Eng +<br/>Governance Lead]

    DRI_APPROVE -->|Yes| PATCH2[Apply Patch]
    DRI_APPROVE -->|No| ALT[Alternative<br/>Patch]
    WAR --> RCA[Root Cause<br/>Analysis]
    RCA --> PATCH3[Reviewed Patch]
    ALT --> PATCH2

    PATCH1 --> SEAL[Seal<br/>Episode]
    PATCH2 --> SEAL
    PATCH3 --> SEAL

    SEAL --> RECALC[Recalculate<br/>Credibility Index]

    style DETECT fill:#0f3460,stroke:#0f3460,color:#fff
    style AUTO fill:#27ae60,stroke:#27ae60,color:#fff
    style REVIEW fill:#f39c12,stroke:#f39c12,color:#fff
    style ESCALATE fill:#c0392b,stroke:#c0392b,color:#fff
```

---

## Credibility Index Components

```mermaid
graph TD
    CI[Credibility Index<br/>~90 / 100] --- TW[Tier-Weighted<br/>Integrity<br/>+42]
    CI --- DP[Drift<br/>Penalty<br/>−4]
    CI --- CR[Correlation<br/>Risk<br/>−6]
    CI --- QM[Quorum<br/>Margin<br/>−2]
    CI --- TTL[TTL<br/>Penalty<br/>−3]
    CI --- IC[Confirmation<br/>Bonus<br/>+3]

    TW --- BASE[Base: 60]

    style CI fill:#0f3460,stroke:#0f3460,color:#fff
    style TW fill:#27ae60,stroke:#27ae60,color:#fff
    style IC fill:#27ae60,stroke:#27ae60,color:#fff
    style DP fill:#c0392b,stroke:#c0392b,color:#fff
    style CR fill:#c0392b,stroke:#c0392b,color:#fff
    style QM fill:#f39c12,stroke:#f39c12,color:#fff
    style TTL fill:#f39c12,stroke:#f39c12,color:#fff
```

---

## Cross-Region Correlation Detection

```mermaid
sequenceDiagram
    participant E as Region East
    participant CT as Correlation Tracker
    participant C as Region Central
    participant DRI as Cross-Region DRI

    E->>CT: Source-CR-017 drift in Domain E3
    C->>CT: Source-CR-017 drift in Domain C2
    CT->>CT: Correlation coefficient > 0.7
    CT->>DRI: Cross-region correlation alert
    DRI->>E: Freeze auto-patching (affected claims)
    DRI->>C: Freeze auto-patching (affected claims)
    DRI->>DRI: Root cause analysis
    DRI->>E: Atomic patch (coordinated)
    DRI->>C: Atomic patch (coordinated)
    E->>CT: Patch applied
    C->>CT: Patch applied
    CT->>CT: Seal cross-region DecisionEpisode
```

---

## Related Diagrams

- [38 — Lattice Architecture](../../mermaid/38-lattice-architecture.md) — Claim → SubClaim → Evidence → Source with Sync Plane and Credibility Index
- [39 — Institutional Drift Loop](../../mermaid/39-drift-loop.md) — Detection → Response → Repair at institutional scale
