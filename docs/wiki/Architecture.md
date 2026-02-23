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
- [System Architecture](../mermaid/01-system-architecture.md)
- [Drift to Patch](../mermaid/05-drift-to-patch.md)
- [Coherence Ops Pipeline](../mermaid/06-coherence-ops-pipeline.md)
- [Integration Map](../mermaid/10-integration-map.md)
- [Seal-and-Prove Pipeline](../mermaid/11-seal-and-prove.md)
- [C-TEC Pipeline](../mermaid/12-c-tec-pipeline.md)
- [Release Preflight Flow](../mermaid/13-release-preflight-flow.md)
- [KPI Confidence Bands Flow](../mermaid/14-kpi-confidence-bands-flow.md)
- [DISR Dual-Mode Architecture](../mermaid/15-disr-dual-mode-architecture.md)
- [Archive Index](../archive/mermaid/ARCHIVE_INDEX.md)
