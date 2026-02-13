# 23 — Core 8 Ontology Graph

> Source: `rdf/ontology/coherence_ops_core.ttl`

```mermaid
graph LR
  subgraph core8["Core 8 Classes"]
    style core8 fill:#1a1a2e,stroke:#0f3460,color:#e0e0e0
    CL([Claim])
    EV([Evidence])
    SA([Source Artifact])
    DE([Decision Episode])
    AS([Assumption])
    OC([Outcome])
    DR([Drift Event])
    PA([Patch])
  end

  subgraph predicates["Key Predicates"]
    style predicates fill:#16213e,stroke:#0f3460,color:#e0e0e0
    EV -->|supports| CL
    EV -->|contradicts| CL
    CL -->|hasEvidence| EV
    EV -->|usesSource| SA
    DE -->|basedOn| AS
    DE -->|decides| CL
    DE -->|resultedIn| OC
    DE -->|driftedInto| DR
    DR -->|patchedBy| PA
  end

  subgraph hooks["Lifecycle Hooks"]
    style hooks fill:#1a1a2e,stroke:#533483,color:#e0e0e0
    AS -->|expiresOn| DATE[xsd:date]
  end

  style CL fill:#0f3460,stroke:#e94560,color:#fff
  style EV fill:#0f3460,stroke:#e94560,color:#fff
  style SA fill:#0f3460,stroke:#e94560,color:#fff
  style DE fill:#533483,stroke:#e94560,color:#fff
  style AS fill:#533483,stroke:#e94560,color:#fff
  style OC fill:#533483,stroke:#e94560,color:#fff
  style DR fill:#e94560,stroke:#fff,color:#fff
  style PA fill:#e94560,stroke:#fff,color:#fff
  style DATE fill:#16213e,stroke:#0f3460,color:#e0e0e0
```

## Reading the Diagram

| Colour | Meaning |
|--------|---------|
| Blue nodes | Evidence chain (Claim, Evidence, Source Artifact) |
| Purple nodes | Decision chain (Decision Episode, Assumption, Outcome) |
| Red nodes | Drift chain (Drift Event, Patch) |
| Labelled edges | OWL Object Properties from `coherence_ops_core.ttl` |

## See Also

- [rdf/ontology/coherence_ops_core.ttl](../rdf/ontology/coherence_ops_core.ttl)
- [rdf/ontology/coherence_ops_extended.ttl](../rdf/ontology/coherence_ops_extended.ttl)
- [05 — Drift to Patch](05-drift-to-patch.md)
- [21 — Coherence Ops Alignment](21-coherence-ops-alignment.md)
