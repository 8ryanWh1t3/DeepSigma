# AL6 — Six Dimensions of Agentic Reliability

The AL6 model defines six dimensions that determine whether an agentic
system is production-safe. Each maps to specific RAL mechanisms.

```mermaid
mindmap
  root((AL6<br/>Agentic<br/>Reliability))
    Deadline
      decisionWindowMs
      stageBudgetsMs
      deadlineMs
    Distance
      hopCount
      fanout
      maxHops / maxFanout
    Data Freshness
      ttlMs
      maxFeatureAgeMs
      ttlBreachesCount
      capturedAt timestamps
    Variability
      p95Ms / p99Ms
      jitterMs
      endToEndMs
    Drag
      queue contention
      lock wait
      IO latency
    Degrade
      cache_bundle
      small_model
      rules_only
      hitl
      abstain / bypass
```

## Dimension to Schema Mapping

```mermaid
graph LR
    subgraph Dimensions
        D1[Deadline]
        D2[Distance]
        D3[Data Freshness]
        D4[Variability]
        D5[Drag]
        D6[Degrade]
    end

    subgraph Schemas
        DTE[DTE Schema]
        EP[Episode Schema]
        AC[Action Contract]
        DR[Drift Schema]
    end

    D1 --> DTE
    D1 --> EP
    D2 --> DTE
    D2 --> EP
    D3 --> DTE
    D3 --> EP
    D4 --> EP
    D4 --> DR
    D5 --> DR
    D6 --> DTE
    D6 --> EP
    D6 --> DR
```
