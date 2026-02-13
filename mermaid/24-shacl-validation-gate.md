# 24 — SHACL Validation Gate

> Source: `rdf/shapes/coherence_ops_core.shacl.ttl`, `rdf/shapes/coherence_ops_extended.shacl.ttl`

```mermaid
flowchart TD
  subgraph ingest["Incoming RDF Triples"]
    style ingest fill:#1a1a2e,stroke:#0f3460,color:#e0e0e0
    TTL[Turtle File<br/>from Extractor]
  end

  TTL --> VALIDATE{SHACL<br/>Validation Engine}

  subgraph shapes["Shape Checks — Core"]
    style shapes fill:#16213e,stroke:#0f3460,color:#e0e0e0
    CS[ClaimShape<br/>hasEvidence ≥ 1]
    DS[DecisionEpisodeShape<br/>wasAttributedTo ≥ 1<br/>decides ≥ 1]
    APS[AssumptionShape<br/>expiresOn xsd:date ≥ 1]
  end

  subgraph ext["Shape Checks — Extended"]
    style ext fill:#16213e,stroke:#533483,color:#e0e0e0
    EXT[Extended SHACL<br/>Shapes]
  end

  VALIDATE --> CS
  VALIDATE --> DS
  VALIDATE --> APS
  VALIDATE --> EXT

  CS --> RESULT{All Shapes<br/>Conform?}
  DS --> RESULT
  APS --> RESULT
  EXT --> RESULT

  RESULT -->|Yes| SEAL[Seal into<br/>Named Graph]
  RESULT -->|No| REPORT[Validation Report<br/>sh:resultMessage]

  SEAL --> SPARQL[SPARQL<br/>Query Pack]
  REPORT --> FIX[Fix & Resubmit]
  FIX --> TTL

  style TTL fill:#0f3460,stroke:#e94560,color:#fff
  style VALIDATE fill:#533483,stroke:#e94560,color:#fff
  style CS fill:#16213e,stroke:#0f3460,color:#e0e0e0
  style DS fill:#16213e,stroke:#0f3460,color:#e0e0e0
  style APS fill:#16213e,stroke:#0f3460,color:#e0e0e0
  style EXT fill:#533483,stroke:#0f3460,color:#e0e0e0
  style RESULT fill:#533483,stroke:#e94560,color:#fff
  style SEAL fill:#0f3460,stroke:#00ff88,color:#fff
  style REPORT fill:#e94560,stroke:#fff,color:#fff
  style SPARQL fill:#0f3460,stroke:#00ff88,color:#fff
  style FIX fill:#e94560,stroke:#fff,color:#fff
```

## Reading the Diagram

| Element | Meaning |
|---------|---------|
| Turtle File | Output of the SharePoint → RDF extractor |
| ClaimShape | Every Claim needs ≥ 1 Evidence link |
| DecisionEpisodeShape | Every Decision needs attribution + ≥ 1 decided Claim |
| AssumptionShape | Every Assumption needs an expiration date |
| Green border | Successful path → sealed graph → SPARQL |
| Red nodes | Failure path → validation report → fix loop |

## See Also

- [rdf/shapes/coherence_ops_core.shacl.ttl](../rdf/shapes/coherence_ops_core.shacl.ttl)
- [rdf/shapes/coherence_ops_extended.shacl.ttl](../rdf/shapes/coherence_ops_extended.shacl.ttl)
- [23 — Core 8 Ontology Graph](23-core8-ontology-graph.md)
- [26 — Named Graph Sealing](26-named-graph-sealing.md)
