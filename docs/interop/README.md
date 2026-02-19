# Interoperability Stack: AG-UI + A2A + MCP + Agora

**One stack. Four protocols. Every layer sealed.**

Σ OVERWATCH treats interoperability not as plumbing but as a first-class decision surface — every protocol handshake, every tool invocation, every agent collaboration produces artifacts subject to Truth · Reasoning · Memory governance.

---

## One Stack View

Modern agentic systems require four distinct communication layers. Each solves a different problem; together they form a complete path from human intent to system execution.

| Layer | Protocol | Bus | Problem Solved |
|-------|----------|-----|----------------|
| **Human → Agent** | AG-UI | Human Interface Bus | Streaming UI events, tool-call rendering, shared state between user and agent |
| **Agent → Agent** | A2A | Agent Bus | Discovery, capability negotiation, task delegation, and status tracking across heterogeneous agents |
| **Agent → Tool** | MCP | Tool Bus | Structured tool/data access — connect any LLM to any tool with schema-typed I/O |
| **Unknown → Known** | Agora | Convergence Bus | Runtime protocol negotiation — two parties that don't share a protocol agree on one dynamically |

### How a request flows

```
Human (AG-UI)
  → Orchestrator Agent
    → Peer Agent (A2A discovery + task card)
      → Tool Call (MCP tool bus)
        → External System
      ← Tool Result (MCP)
    ← Agent Result (A2A)
  ← Streamed Response (AG-UI)
```

Every arrow above is a potential drift surface. Σ OVERWATCH seals each transition.

---

## Layer-by-Layer

1. **AG-UI (Human Interface Bus)** — Standardizes how agents stream partial results, render tool calls, and share state with UIs. Replaces ad-hoc SSE/WebSocket implementations with a typed event protocol.

2. **A2A (Agent Bus)** — Google's agent-to-agent protocol. Agents publish Agent Cards describing capabilities, authentication, and endpoints. Other agents discover and delegate tasks via a structured JSON-RPC interface. Solves the "how do I find and talk to another agent" problem.

3. **MCP (Tool Bus)** — Anthropic's Model Context Protocol. Provides a uniform interface for LLMs to call tools, read resources, and receive prompts. Eliminates per-tool integration code. The lingua franca of tool access.

4. **Agora (Convergence Bus)** — The meta-protocol. When two systems don't share a common protocol, Agora uses LLM-assisted negotiation to: (a) discover each party's capabilities, (b) generate a **ProtocolContract** both sides agree to, (c) compile that contract into executable **routines** that run without further LLM calls. Reduces ongoing LLM cost to near-zero for repeated interactions.

---

## Why Agora Is Different

AG-UI, A2A, and MCP are **standards** — they define fixed wire formats. Agora is **convergence machinery** — it generates standards on the fly when no existing standard fits.

| Aspect | Standards (AG-UI / A2A / MCP) | Agora |
|--------|-------------------------------|-------|
| **When useful** | Both sides already speak the same protocol | Parties have incompatible or unknown protocols |
| **LLM involvement** | None at runtime | Only during negotiation; compiled routines run without LLM |
| **Output** | Messages conforming to spec | A sealed ProtocolContract + executable routines |
| **Drift surface** | Schema/version changes | Schema, semantic, capability, and policy drift |
| **Coherence Ops role** | Seal tool calls, version schemas | Seal contracts, version routines, detect drift, patch |

Agora doesn't replace MCP or A2A — it fills the gap when you encounter a system that speaks neither.

---

## Coherence Ops Integration

Every interop event maps to Σ OVERWATCH primitives:

| Interop Event | Artifact | Primitive |
|---------------|----------|-----------|
| Protocol contract negotiated | DLR (contract sealed) | Truth |
| Negotiation rationale captured | RS (why this contract) | Reasoning |
| Contract stored for reuse | DS + MG (template + graph) | Memory |
| Schema changes detected | Drift Event | Drift |
| Contract renegotiated | Patch + new DLR | Patch |
| "Why did we choose this protocol?" | IRIS query | Recall |

---

## Related Files

| Resource | Purpose |
|----------|---------|
| [Gateway Spec v0.1](COHERENCE_INTEROP_GATEWAY_SPEC_v0.1.md) | Production-oriented gateway architecture |
| [Drift Triggers](DRIFT_TRIGGERS.md) | Drift detection signals and response playbook |
| [MVP Plan](MVP_PLAN.md) | 2-week implementation plan |
| [ProtocolContract Schema](../../schemas/interop/protocol_contract.schema.json) | JSON Schema for sealed contracts |
| [Example Contract](../../templates/interop/ProtocolContract.example.json) | Realistic AgentBooking ↔ AgentTravel example |
| [Mermaid: Interop Flow](../../mermaid/30-interop-request-flow.md) | Sequence diagram |
| [Mermaid: Agora Negotiation](../../mermaid/31-agora-negotiation-flow.md) | Negotiation flowchart |
