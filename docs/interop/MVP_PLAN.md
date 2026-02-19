# Interop Gateway — MVP Plan (2 Weeks)

**Version:** 0.1.0
**Target Release:** v0.6.1
**Duration:** 14 days
**Goal:** Ship a working gateway that negotiates a contract, compiles a routine, detects drift, patches, and produces a before/after coherence score — all in one demo.

---

## Demo Scenario (Money Demo)

> **"Tool schema changes → drift detected → renegotiate → patched routine → before/after coherence score"**

A MCP tool server changes its `search_flights` tool schema (adds a required field). The gateway:

1. Detects the schema drift on the next call.
2. Classifies it as `schema` drift, severity `medium`.
3. Auto-renegotiates: generates a new contract version with the updated field mapping.
4. Compiles the patched routine.
5. Re-executes the call successfully.
6. Produces a coherence report: baseline score (pre-drift) vs. patched score (post-recovery).

**Expected output:**
```
BASELINE  92.00 (A)  → DRIFT 74.50 (C) → PATCH 92.00 (A)
Drift events: 1 (schema, medium)
Contract: v1.0.0 → v1.1.0
Routine recompiled: yes
LLM calls during patch: 1 (renegotiation)
Total elapsed: < 15s
```

---

## Daily Milestones

### Phase 1: Adapters + Contract Sealing (Days 1–3)

**Day 1 — Scaffold**
- [ ] Create `gateway/` module structure:
  ```
  gateway/
  ├── __init__.py
  ├── adapters/
  │   ├── __init__.py
  │   ├── base.py          # ProtocolAdapter ABC
  │   ├── mcp_adapter.py
  │   ├── a2a_adapter.py
  │   ├── agui_adapter.py
  │   └── unknown_adapter.py
  ├── contracts/
  │   ├── __init__.py
  │   ├── sealer.py        # ContractSealer
  │   └── store.py         # ContractStore (in-memory + file)
  ├── negotiation/
  │   ├── __init__.py
  │   └── engine.py        # NegotiationEngine
  ├── runtime/
  │   ├── __init__.py
  │   ├── compiler.py      # RoutineCompiler
  │   └── executor.py      # RoutineExecutor
  ├── drift/
  │   ├── __init__.py
  │   └── sensor.py        # InteropDriftSensor
  └── config.py
  ```
- [ ] Implement `ProtocolAdapter` ABC: `probe()`, `transform_request()`, `transform_response()`, `name`
- [ ] Implement `MCP Adapter` (wraps existing MCP client)
- [ ] Unit tests for adapter interface

**Day 2 — Contract Sealer**
- [ ] Implement `ContractSealer`: takes negotiation output → produces sealed `ProtocolContract`
- [ ] SHA-256 hashing of canonical JSON
- [ ] Version management: `supersedes` chain
- [ ] `ContractStore`: save/load from JSON files, lookup by `contract_id` or participant pair
- [ ] Unit tests: sealing, hashing determinism, version chain

**Day 3 — A2A + AG-UI Adapters**
- [ ] Implement `A2A Adapter` (Agent Card fetch, task delegation stub)
- [ ] Implement `AG-UI Adapter` (event stream normalization stub)
- [ ] Integration test: MCP adapter → seal → store → retrieve

**Demo checkpoint (Day 3):** Can seal a contract from a known MCP tool server and retrieve it by ID.

---

### Phase 2: Negotiation + Routine Generation (Days 4–6)

**Day 4 — Negotiation Engine Skeleton**
- [ ] Implement `NegotiationEngine`:
  - `probe(party_a, party_b)` → capability descriptors
  - `match(descriptors)` → known adapter or `None`
  - `negotiate(descriptors)` → `ProtocolContract` draft (LLM call)
- [ ] Max 3 rounds, 30s timeout per round
- [ ] Fixture mode: pre-recorded negotiation for deterministic tests

**Day 5 — Routine Compiler**
- [ ] Implement `RoutineCompiler`:
  - Takes `ProtocolContract` → produces `Routine` (field mappings, transforms, error handlers)
  - Routine is a declarative object (not executable code)
- [ ] `RoutineExecutor`: applies routine to incoming request → transformed request
- [ ] Unit tests: compile → execute round-trip

**Day 6 — Cache + Lookup**
- [ ] LRU cache for compiled routines (keyed by `contract_id`)
- [ ] Lookup by participant pair (for repeat interactions)
- [ ] Cache eviction + metrics
- [ ] Integration test: negotiate → compile → cache → execute (no LLM on second call)

**Demo checkpoint (Day 6):** Full negotiate → compile → execute cycle. Second call hits cache (0 LLM calls).

---

### Phase 3: Runtime + Trace Propagation (Days 7–9)

**Day 7 — Runtime Engine**
- [ ] Implement retry logic: 3 attempts, exponential backoff
- [ ] Circuit breaker: open after 5 failures, half-open after 30s
- [ ] Timeout enforcement per contract constraints
- [ ] Degrade ladder integration (L0–L3)

**Day 8 — Trace Propagation**
- [ ] W3C Trace Context propagation through all gateway spans
- [ ] OpenTelemetry span creation: `gateway.receive`, `adapter.transform`, `runtime.invoke`, `coherence.seal`
- [ ] Integration with existing OTel adapter (`adapters/otel/`)
- [ ] Unit tests for span hierarchy

**Day 9 — Observability Metrics**
- [ ] Implement counters/histograms:
  - `interop.time_to_first_call`
  - `interop.repeat_call_llm_pct`
  - `interop.contract_cache_hit_rate`
  - `interop.circuit_breaker_trips`
- [ ] Metrics export compatible with existing dashboard

**Demo checkpoint (Day 9):** Full runtime with retries, circuit breaker, and trace propagation visible in OTel export.

---

### Phase 4: Drift Triggers + Patch Workflow (Days 10–12)

**Day 10 — Drift Sensor**
- [ ] Implement `InteropDriftSensor`:
  - Schema drift: response validation against contract schema
  - Capability drift: Agent Card / tool manifest diff
  - Performance drift: latency/error rate sliding window
- [ ] Drift event emission conforming to `specs/drift.schema.json`

**Day 11 — Patch Workflow**
- [ ] Wire drift sensor → classify → response pipeline:
  - Low: log + DS entry
  - Medium: auto-renegotiate → new contract version → recompile routine
  - High: block + escalate
  - Critical: circuit break + incident DLR
- [ ] Patch sealed as DLR; MG updated
- [ ] Coherence score recomputed post-patch

**Day 12 — Freshness + Policy Drift**
- [ ] Contract TTL monitor (warning at 80%, critical at 100%)
- [ ] Policy drift detection (auth probe on 401/403)
- [ ] Integration test: full drift → patch → score recovery cycle

**Demo checkpoint (Day 12):** Schema drift detected → auto-renegotiated → patched routine → coherence score recovered.

---

### Phase 5: Money Demo + Polish (Days 13–14)

**Day 13 — Money Demo Packaging**
- [ ] Create `demos/interop_money_demo/`:
  - `fixtures/`: Pre-recorded MCP tool manifest (v1 and v2 with schema change)
  - `run_demo.py`: Orchestrates the full scenario
  - `expected/`: Golden-file expected outputs
- [ ] CLI integration: `deepsigma interop-demo` or `python -m demos.interop_money_demo`
- [ ] Output: step-by-step JSON artifacts + summary with before/after scores

**Day 14 — README Polish + CI**
- [ ] Update docs/interop/README.md with demo instructions
- [ ] Add `test_interop_gateway.py` to CI
- [ ] Lint pass (`ruff check`)
- [ ] Full test suite green
- [ ] Version bump to 0.6.1 in pyproject.toml
- [ ] CHANGELOG entry

**Demo checkpoint (Day 14):** One-command Money Demo runs end-to-end. CI green. Docs complete.

---

## Test Coverage Targets

| Module | Target | Test Type |
|--------|--------|-----------|
| Adapters | 90% | Unit |
| Contract Sealer/Store | 95% | Unit |
| Negotiation Engine | 85% | Unit + fixture integration |
| Routine Compiler/Executor | 90% | Unit |
| Runtime (retry/circuit) | 90% | Unit |
| Drift Sensor | 85% | Unit + integration |
| Patch Workflow | 85% | Integration |
| Money Demo | 100% (golden-file) | E2E |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Existing MCP adapter | Shipped (v0.5.0) | Wrapping, not rewriting |
| Existing OTel adapter | Shipped (v0.5.0) | Extending with gateway spans |
| Existing drift system | Shipped (v0.5.1) | `DeltaDriftDetector` extended |
| Existing coherence scorer | Shipped (v0.3.0) | Used for before/after scoring |
| LLM access for negotiation | Optional | Fixture mode works without API key |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| LLM negotiation quality varies | Fixture mode for deterministic tests; max 3 rounds |
| A2A spec still evolving | Adapter is a thin wrapper; isolate A2A-specific logic |
| Scope creep into full A2A/AG-UI implementation | Gateway is glue, not a full protocol stack — delegate to upstream libs |
| Performance overhead from sealing every call | Async sealing; batch writes to MG |
