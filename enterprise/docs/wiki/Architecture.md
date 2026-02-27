# Architecture

RAL sits between **agent frameworks** and **data/action planes**.

```text
Agent Frameworks (LangChain/LangGraph/etc)
          |
          v
   ┌───────────────────────────────┐
   │  RAL / Σ OVERWATCH (Control)   │
   │  - DTE deadlines & budgets     │
   │  - TTL / TOCTOU freshness      │
   │  - Safe Action Contract        │
   │  - Verification                │
   │  - Sealing + Drift→Patch       │
   └───────────────────────────────┘
          |
          v
Data / Action Planes (Foundry, APIs, Power Platform, etc)
```

Transport options:
- **MCP server** (recommended) or MCP gateway
- Direct adapters (LangChain callbacks/tool wrappers)

See also: [Runtime Flow](Runtime-Flow)

Mermaid diagrams:
- [System Architecture](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/01-system-architecture.md)
- [Drift to Patch](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/05-drift-to-patch.md)
- [Coherence Ops Pipeline](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/06-coherence-ops-pipeline.md)
- [Integration Map](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/10-integration-map.md)
- [Seal-and-Prove Pipeline](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/11-seal-and-prove.md)
- [C-TEC Pipeline](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/12-c-tec-pipeline.md)
- [Release Preflight Flow](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/13-release-preflight-flow.md)
- [KPI Confidence Bands Flow](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/14-kpi-confidence-bands-flow.md)
- [DISR Dual-Mode Architecture](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/15-disr-dual-mode-architecture.md)
- [Authority Boundary Primitive](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/16-authority-boundary-primitive.md)
- [Authority + Economic Evidence Pipeline](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/22-authority-economic-evidence.md)
- [Archive Index](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/archive/mermaid/ARCHIVE_INDEX.md)
