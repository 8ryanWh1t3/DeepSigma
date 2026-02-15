# 27 — PRIME Threshold Gate

> LLM output → PRIME gate → Decision-grade action

## Overview

The PRIME Threshold Gate sits between context assembly and action execution
in the Coherence Ops pipeline. It evaluates Truth-Reasoning-Memory invariants
and emits one of three verdicts: **APPROVE**, **DEFER**, or **ESCALATE**.

## Gate Flow

```mermaid
flowchart TD
    A[Raw LLM Output] --> B[Context Assembly]
    B --> C{PRIME Gate}

    C --> D[Truth Invariant]
    C --> E[Reasoning Invariant]
    C --> F[Memory Invariant]

    D --> D1[Claim-Evidence-Source]
    D --> D2[Confidence Band]
    D --> D3[Disconfirmers Check]

    E --> E1[Facts vs Interpretations]
    E --> E2[Assumption TTL Check]
    E --> E3[Fact Ratio Score]

    F --> F1[Seal Verification]
    F --> F2[Version Lineage]
    F --> F3[Patch History]

    D1 & D2 & D3 --> G[Truth Score]
    E1 & E2 & E3 --> H[Reasoning Score]
    F1 & F2 & F3 --> I[Memory Score]

    G & H & I --> J[Composite Score]
    J --> K{Escalation Triggers?}

    K -->|Temperature > Ceiling| L[ESCALATE]
    K -->|Missing Seal| L
    K -->|Contested + Escalate Policy| L
    K -->|No Triggers + Score >= 0.7| M[APPROVE]
    K -->|No Triggers + Score >= 0.4| N[DEFER]
    K -->|Score < 0.4| L

    M --> O[Execute Action]
    N --> P[Queue for Review]
    L --> Q[Human Escalation]

    O & P & Q --> R[Episode Record]
    R --> S[Decision Lineage]

    style A fill:#1a2740,stroke:#38bdf8,color:#e2e8f0
    style C fill:#0d1420,stroke:#ffb84d,color:#ffb84d,stroke-width:3px
    style M fill:#0d1420,stroke:#00e5a0,color:#00e5a0
    style N fill:#0d1420,stroke:#38bdf8,color:#38bdf8
    style L fill:#0d1420,stroke:#ff4d6a,color:#ff4d6a
```

## Scoring Weights

| Component         | Weight | Source                    |
|--------------------|--------|---------------------------|
| Truth Score        | 40%    | Claim confidence + evidence ratio |
| Reasoning Score    | 30%    | Fact ratio - assumption penalty   |
| Memory Score       | 15%    | Seal + lineage + version          |
| Coherence Score    | 15%    | External coherence scorer         |

## Verdict Decision Matrix

```mermaid
flowchart LR
    subgraph Verdicts
        A[Composite >= 0.7<br/>No escalation triggers] -->|APPROVE| B((Execute))
        C[Composite >= 0.4<br/>Defer-class triggers] -->|DEFER| D((Queue))
        E[Composite < 0.4<br/>OR hard triggers] -->|ESCALATE| F((Human))
    end

    style B fill:#00e5a0,color:#06090f,stroke:#00e5a0
    style D fill:#38bdf8,color:#06090f,stroke:#38bdf8
    style F fill:#ff4d6a,color:#06090f,stroke:#ff4d6a
```

## Hard Escalation Triggers

These bypass the composite score and force ESCALATE:

1. **Temperature breach** — System temperature exceeds configured ceiling
2. **Missing seal** — Memory seal required but absent (when `require_seal=True`)
3. **Contested claim** — Active disconfirmers present (when policy = "escalate")
4. **Expired assumptions** — Too many expired assumptions in reasoning context

## Pipeline Position

```mermaid
flowchart LR
    A[Context<br/>Assembly] --> B[PRIME<br/>Gate]
    B --> C[Action<br/>Execution]
    B --> D[Episode<br/>Record]

    subgraph "Coherence Ops Pipeline"
        A
        B
        C
        D
    end

    E[DLR] -.-> A
    F[RS] -.-> A
    G[DS] -.-> A
    H[MG] -.-> A

    style B fill:#ffb84d,color:#06090f,stroke:#ffb84d,stroke-width:3px
```

## Configuration

See `specs/prime_gate.schema.json` for the full schema.

Key config parameters:
- `approve_threshold`: Minimum composite for APPROVE (default: 0.7)
- `defer_threshold`: Minimum composite for DEFER (default: 0.4)
- `temperature_ceiling`: Max system temperature before forced ESCALATE (default: 0.8)
- `require_seal`: Whether memory seal is mandatory (default: false)
- `contested_claim_policy`: "defer" or "escalate" (default: "defer")

## Related

- [coherence_ops/prime.py](../coherence_ops/prime.py) — Implementation
- [specs/prime_gate.schema.json](../specs/prime_gate.schema.json) — JSON Schema
- [tests/test_prime.py](../tests/test_prime.py) — Unit tests
- [docs/17-prime.md](../docs/17-prime.md) — Full documentation
