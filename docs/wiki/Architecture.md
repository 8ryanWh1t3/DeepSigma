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
