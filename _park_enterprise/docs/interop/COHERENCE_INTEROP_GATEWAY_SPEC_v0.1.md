# Coherence Ops Interop Gateway — Spec v0.1

**Version:** 0.1.0
**Status:** Draft
**Target Release:** v0.6.1

---

## Overview

The Coherence Ops Interop Gateway is the boundary component that connects Σ OVERWATCH to external protocols — MCP tool servers, A2A agent networks, AG-UI frontends, and unknown systems requiring runtime negotiation. Every message crossing this boundary is sealed, versioned, and subject to drift detection.

### Problem Statement

Agentic systems interact through a growing set of incompatible protocols. Each integration today requires:

- Custom adapter code per protocol
- Manual schema alignment with no versioning
- No provenance trail for inter-agent decisions
- No detection when a peer's schema, capabilities, or policies change
- No mechanism to renegotiate when changes occur

The result: brittle integrations that fail silently, with no institutional memory of why a particular protocol choice was made or when it stopped being valid.

### Design Principles

1. **Seal everything** — Every contract, routine, and tool invocation produces a sealed artifact.
2. **No overwrite** — Contracts are versioned. Changes produce new versions, not mutations.
3. **Assumptions expire** — Every contract has a TTL. Stale contracts trigger drift review.
4. **Provenance required** — Every claim traces to evidence, every evidence to a source.
5. **LLM cost amortized** — Negotiation uses LLM once; compiled routines run without LLM.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Interop Gateway                        │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │  AG-UI   │ │   A2A    │ │   MCP    │ │  Unknown   │  │
│  │ Adapter  │ │ Adapter  │ │ Adapter  │ │  Adapter   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       │             │            │              │         │
│       └─────────────┴────────────┴──────────────┘        │
│                          │                               │
│                 ┌────────▼────────┐                      │
│                 │   Negotiation   │                      │
│                 │     Engine      │                      │
│                 └────────┬────────┘                      │
│                          │                               │
│            ┌─────────────┼─────────────┐                 │
│            │             │             │                  │
│     ┌──────▼──────┐ ┌───▼───┐ ┌──────▼──────┐          │
│     │   Contract  │ │Runtime│ │    Drift     │          │
│     │   Sealer    │ │Engine │ │   Sensor     │          │
│     └──────┬──────┘ └───┬───┘ └──────┬──────┘          │
│            │             │            │                   │
│            └─────────────┴────────────┘                  │
│                          │                               │
│                 ┌────────▼────────┐                      │
│                 │  Coherence Ops  │                      │
│                 │  DLR·RS·DS·MG   │                      │
│                 └─────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

---

## Protocol Adapters

Each adapter normalizes a specific protocol into the gateway's internal canonical message format.

### MCP Adapter

**Direction:** Agent → Tools/Resources

| Capability | Implementation |
|------------|----------------|
| Tool discovery | `tools/list` → adapter caches tool schemas |
| Tool invocation | `tools/call` → sealed as DLR action |
| Resource access | `resources/read` → sealed with provenance |
| Schema tracking | Hash tool schemas; detect changes between sessions |

**Sealing:** Every `tools/call` produces a DLR action entry with `tool_id`, `input_hash`, `output_hash`, and `latency_ms`.

### A2A Adapter

**Direction:** Agent ↔ Agent

| Capability | Implementation |
|------------|----------------|
| Discovery | Fetch Agent Cards from well-known endpoints |
| Task delegation | `tasks/send` → sealed as RS (reasoning for delegation) |
| Status tracking | `tasks/get` → drift monitor for stalled tasks |
| Streaming | `tasks/sendSubscribe` → AG-UI event bridge |

**Sealing:** Delegation decisions produce RS entries documenting why agent X was selected over alternatives.

### AG-UI Adapter

**Direction:** Human ↔ Agent

| Capability | Implementation |
|------------|----------------|
| Event streaming | SSE/WebSocket events normalized to typed stream |
| Tool rendering | Tool call events → UI component dispatch |
| State sync | Shared context between UI state and agent state |
| Approval gates | Human-in-the-loop for high-severity patches |

**Sealing:** User approvals produce DLR entries with `actor.type = "human"`.

### Unknown Protocol Adapter

**Direction:** Any ↔ Any (via Agora negotiation)

| Capability | Implementation |
|------------|----------------|
| Capability probing | Exchange descriptors in natural language or schema |
| Contract generation | LLM-assisted negotiation → ProtocolContract |
| Routine compilation | Contract → deterministic execution routine |
| Fallback | If negotiation fails → degrade to manual integration |

**Sealing:** The negotiation itself is sealed as a full Decision Episode: intent → reasoning → outcome → contract.

---

## Negotiation Engine (Agora-Style)

The negotiation engine handles the case where two parties lack a shared protocol.

### Negotiation Flow

1. **Probe** — Each party publishes a capability descriptor: supported message types, field schemas, authentication methods, rate limits.
2. **Match** — Engine checks if any known adapter (MCP, A2A, AG-UI) satisfies both descriptors. If yes, route through that adapter.
3. **Generate** — If no match, invoke LLM with both descriptors to draft a `ProtocolContract`.
4. **Validate** — Both parties validate the draft against their constraints. Counter-proposals loop back to generation (max 3 rounds).
5. **Seal** — Accepted contract is sealed with `contract_id`, `version`, `hash`, `expiry`, and `provenance`.
6. **Compile** — Contract compiles into an executable routine: field mappings, transforms, error handlers.
7. **Cache** — Routine cached by `contract_id`. Subsequent calls execute without LLM.

### Negotiation Limits

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max negotiation rounds | 3 | Prevent infinite loops |
| Max contract TTL | 30 days | Force periodic revalidation |
| Min contract TTL | 1 hour | Allow short-lived experiments |
| LLM timeout per round | 30s | Bound negotiation latency |
| Routine cache eviction | LRU, 1000 entries | Bound memory |

---

## Sealing and Versioning

Every artifact produced by the gateway follows the Coherence Ops seal discipline.

### Contract Lifecycle

```
v1 (sealed) → active → drift detected → v2 (negotiated) → sealed → active → ...
```

Contracts are **never mutated**. A change produces a new version. The previous version's DLR records `superseded_by: contract_id_v2`.

### Sealed Fields

| Field | Type | Purpose |
|-------|------|---------|
| `contract_id` | UUID | Unique identifier |
| `version` | SemVer string | Contract version |
| `hash` | SHA-256 | Content-addressable integrity |
| `sealed_at` | ISO 8601 | Seal timestamp |
| `expiry` | ISO 8601 | Assumption half-life — when this contract must be revalidated |
| `provenance` | Array | Chain: negotiation_id → parties → evidence |
| `participants` | Array | Party descriptors with roles |
| `supersedes` | UUID or null | Previous contract version |

### Provenance Chain

```
ProtocolContract.provenance[0]
  → negotiation_session_id
    → party_a.capability_descriptor
    → party_b.capability_descriptor
    → llm_model_used (if Agora)
    → negotiation_rounds
    → human_approver (if required)
```

---

## Runtime Engine

Once a contract is sealed and compiled, the runtime engine executes routines without LLM involvement.

### Execution Model

1. **Lookup** — Incoming request matched to cached routine by `contract_id` or participant pair.
2. **Transform** — Input fields mapped per routine's field mapping table.
3. **Invoke** — Transformed request sent to target system.
4. **Validate** — Response validated against contract's response schema.
5. **Seal** — Invocation recorded as DLR action.

### Retry and Circuit Breakers

| Behavior | Configuration |
|----------|---------------|
| Retries | 3 attempts, exponential backoff (1s, 2s, 4s) |
| Circuit breaker | Open after 5 consecutive failures; half-open after 30s |
| Timeout | Per-call: 10s default, configurable per contract |
| Fallback | Degrade ladder: cached response → default response → error |

### Degrade Ladder Integration

The gateway integrates with Σ OVERWATCH's existing degrade ladder:

| Level | Trigger | Behavior |
|-------|---------|----------|
| L0 — Normal | All systems nominal | Full pipeline |
| L1 — Degraded | Peer latency > 2× baseline | Skip non-critical enrichment |
| L2 — Fallback | Peer unreachable | Use cached last-known-good response |
| L3 — Offline | Circuit breaker open | Queue requests, emit drift event |

---

## Observability

### Trace Propagation

Every gateway call propagates a `trace_id` through all layers:

```
trace_id (W3C Trace Context)
  → span: gateway.receive
    → span: adapter.{protocol}.transform
      → span: runtime.invoke
        → span: external.{target}
      → span: runtime.validate
    → span: coherence.seal
```

Compatible with OpenTelemetry. Spans export via the existing OTel adapter (`adapters/otel/`).

### Metrics

| Metric | Type | SLO |
|--------|------|-----|
| `interop.time_to_first_call` | Histogram | p95 < 500ms (known protocol), p95 < 10s (negotiation) |
| `interop.repeat_call_llm_pct` | Gauge | < 1% (compiled routines should not need LLM) |
| `interop.contract_cache_hit_rate` | Gauge | > 95% |
| `interop.drift_detect_latency` | Histogram | p95 < 2s |
| `interop.patch_latency` | Histogram | p95 < 30s (auto), p95 < 5min (human-approved) |
| `interop.negotiation_rounds` | Histogram | p50 = 1, p95 ≤ 3 |
| `interop.circuit_breaker_trips` | Counter | < 5/hour |

---

## Drift Sensor + Patch Loop

The drift sensor continuously monitors live interop traffic against sealed contracts.

### Detection Signals

1. **Schema drift** — Response fields don't match contract's response schema.
2. **Semantic drift** — Fields present but values have changed meaning (e.g., status codes renumbered).
3. **Capability drift** — Peer's Agent Card or tool manifest changed.
4. **Policy drift** — Access control, rate limits, or authentication requirements changed.
5. **Performance drift** — Latency or error rates exceed contract's SLO thresholds.

### Response Pipeline

```
Drift Signal
  → Classify (type + severity)
    → severity=low:  Log + emit DS entry
    → severity=medium: Auto-renegotiate (new contract version)
    → severity=high: Block traffic + require human approval
    → severity=critical: Circuit break + escalate + incident DLR
  → Patch sealed as DLR
  → MG updated with new contract version
  → Coherence score recomputed
```

See [DRIFT_TRIGGERS.md](DRIFT_TRIGGERS.md) for the full trigger table.

---

## Security

### Minimum Viable Controls

| Control | Implementation |
|---------|----------------|
| **Identity** | Each party identified by verifiable ID (URI, DID, or API key fingerprint) |
| **Authentication** | Mutual TLS or OAuth 2.0 bearer tokens; no anonymous negotiation |
| **Authorization** | Policy gates per contract: which tools, which data, which actions |
| **Signed contracts** | ProtocolContract `hash` field = SHA-256 of canonical JSON; optional Ed25519 signature |
| **Least privilege tool scopes** | MCP tool calls restricted to contract's declared `tool_scopes` |
| **Policy gates** | Pre-execution policy check against active policy pack (e.g., `no_pii_export`, `max_blast_radius`) |
| **Injection defense** | Input sanitization on all contract fields; routine compilation rejects executable content |
| **Replay protection** | Nonce + timestamp on negotiation messages; contracts have `expiry` |

### Threat Model (Key Risks)

| Threat | Mitigation |
|--------|------------|
| Malicious contract proposal | Validation against schema + policy gates before acceptance |
| Capability spoofing | Verify Agent Card signatures; probe actual capabilities |
| Routine injection | Compiled routines are declarative (field mappings), not executable code |
| Contract replay | Nonce binding; `sealed_at` + `expiry` enforce temporal validity |
| Exfiltration via tool calls | Least-privilege scopes; output schema validation |

---

## Failure Modes

| Mode | Detection | Impact | Recovery |
|------|-----------|--------|----------|
| **Schema mismatch** | Response validation fails | Invocation returns error | Re-negotiate or apply field mapping patch |
| **Semantic mismatch** | Downstream logic errors; coherence score drops | Silent incorrect behavior | Detect via coherence scoring; renegotiate |
| **Capability change** | Agent Card diff or tool manifest diff | Tool calls fail or return unexpected types | Re-probe + re-negotiate |
| **Injection attempt** | Input sanitization flags | Negotiation blocked | Log, alert, block party |
| **Replay attack** | Nonce/timestamp validation | Stale contract accepted | Reject; require fresh negotiation |
| **Negotiation deadlock** | Round count exceeds max | No contract established | Fallback to manual integration; escalate |
| **Performance degradation** | Latency/error SLO breach | User-visible slowdown | Circuit breaker → degrade ladder |

---

## Success Metrics / SLOs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time-to-first-call (known protocol) | p95 < 500ms | From gateway receipt to first successful invocation |
| Time-to-first-call (negotiation) | p95 < 10s | From probe start to first routine execution |
| Repeat-call non-LLM % | > 99% | Compiled routines executing without LLM fallback |
| Drift detection latency | p95 < 2s | From drift signal to classified drift event |
| Patch latency (auto) | p95 < 30s | From drift event to sealed patch |
| Patch latency (human-approved) | p95 < 5min | From escalation to sealed patch |
| Contract cache hit rate | > 95% | Routine lookups served from cache |
| Coherence score post-patch | ≥ baseline | Patched score must meet or exceed pre-drift baseline |
