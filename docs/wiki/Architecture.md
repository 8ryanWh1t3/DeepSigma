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

See also: [Runtime Flow](Runtime-Flow.md)

Mermaid diagrams:
- [System Architecture](../mermaid/01-system-architecture.md)
- [Drift to Patch](../mermaid/05-drift-to-patch.md)
- [Coherence Ops Pipeline](../mermaid/06-coherence-ops-pipeline.md)
- [Integration Map](../mermaid/10-integration-map.md)
- [C-TEC Pipeline](../mermaid/12-c-tec-pipeline.md)
