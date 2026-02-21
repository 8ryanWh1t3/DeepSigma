# Changelog

All notable changes to Σ OVERWATCH / DeepSigma will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] — 2026-02-21 — "Clean Foundations"

### Changed

- **Canonical 9-folder structure**: Repo root reduced from 30+ items to 9 tracked folders + standard config files
- `specs/` → `schemas/core/`, `templates/` → `artifacts/templates/`, `examples/` → `docs/examples/`, `fixtures/` → `tests/fixtures/`, `mdpt/` → `src/mdpt/` (PR #176)
- 6 variant Dockerfiles moved to `docker/` subdirectory (PR #177)
- `HERO_DEMO.md`, `STABILITY.md`, `START_HERE.md` moved into `docs/` (PR #178)
- `sample_data/` → `artifacts/sample_data/`, `scripts/` → `src/tools/prompt_os/` (PR #179)
- ~50 internal links rebased; ~15 pre-existing broken links fixed as side-effect
- `.dockerignore` updated: `!docs/examples/` allowlist, removed stale entries
- 5 variant Dockerfiles fixed: `COPY specs/` → `COPY schemas/`, `COPY examples/` → `COPY docs/examples/`

### Added

- **Prompt OS A–E** (PR #175): Sample data CSVs, JSON schema, validation scripts, sealed run export, CI workflow with drift guards

### Stats

- 0 new features, 0 breaking changes — structural cleanup only
- All 1050+ tests pass, all Docker images build, all CI green

---

## [1.0.0] — 2026-02-19 — "Distributed Credibility Mesh"

### Added

- **Mesh Node Runtime** (`mesh/node_runtime.py`): Multi-node architecture with 4 roles — edge, validator, aggregator, seal-authority. Thread-based node processes with independent state and replication
- **Signed Evidence Envelopes** (`mesh/envelopes.py`, `mesh/crypto.py`): Ed25519-compatible signing (HMAC-SHA256 demo fallback). Every envelope carries payload hash + signature for tamper evidence
- **HTTP Replication** (`mesh/transport.py`): Push/pull transport for append-only log synchronization between nodes. FastAPI router under `/mesh/*` prefix
- **Federated Quorum** (`mesh/federation.py`): Policy-driven quorum across regions + correlation groups. Claims cannot reach VERIFIED without multi-region, multi-group consensus. Partition → UNKNOWN (safe default)
- **Mesh Scenarios** (`mesh/scenarios.py`): 4-phase scenario controller — healthy baseline, partition (region B offline), correlated failure (region C INVALID), recovery via patch
- **Cross-Node Verification** (`mesh/verify.py`): Envelope signature verification, seal chain continuity checks, cross-node coverage reports
- **Mesh CLI** (`mesh/cli.py`): `python -m mesh.cli init`, `run`, `scenario` commands for demo operation
- **Mesh Summary Endpoint**: `GET /mesh/{tenant_id}/summary` — node statuses, last aggregate, last seal, verification health
- **Append-Only Logstore** (`mesh/logstore.py`): Atomic JSONL writes with temp-file rename pattern. Deduplication by ID field

### Changed

- `pyproject.toml`: Version 0.9.0 → 1.0.0, added `mesh*` to package discovery
- `credibility_engine/__init__.py`: Version bump
- `dashboard/api_server.py`: Mesh router integration
- `CHANGELOG.md`: v1.0.0 entry

### Stats

- 11 new files, 4 modified, v0.9.0 governance + credibility APIs preserved, abstract institutional modeling preserved

---

## [0.9.0] — 2026-02-19 — "Governance Hardening"

### Added

- **Per-Tenant Policy Engine** (`tenancy/policies.py`): Tenant-scoped policy files with TTL, quorum, correlation, silence, SLO, and quota thresholds. Policy evaluation produces violation lists and SHA-256 policy hashes
- **Seal Chaining** (`credibility_engine/packet.py`): Tamper-evident continuity — each seal links to the previous seal via `prev_seal_hash`, includes `policy_hash` and `snapshot_hash`. Seal chain persisted to `seal_chain.jsonl`
- **Immutable Audit Trail** (`governance/audit.py`): Append-only audit log for critical actions (PACKET_GENERATE, PACKET_SEAL, SNAPSHOT_WRITE, POLICY_UPDATE). Denied attempts are always audited
- **Drift Recurrence Weighting** (`governance/drift_registry.py`): Fingerprint registry tracks 24h/7d recurrence counts. Severity multipliers: >10 = 1.5x, >25 = 2.0x, >50 = 3.0x
- **Quotas + SLO Telemetry** (`governance/telemetry.py`): Per-tenant rate limits on packet generation/sealing. Exceeding quota returns HTTP 429 + audit event. Tracks `packet_generate_latency_ms` and `packet_seal_latency_ms`
- **Policy API Endpoints**: `GET /api/{tenant_id}/policy`, `POST /api/{tenant_id}/policy` (requires `truth_owner` or `coherence_steward`)
- **Audit API Endpoint**: `GET /api/{tenant_id}/audit/recent?limit=50` (read-only)
- **Seeded Policy Files**: 3 demo tenant policies with distinct configurations (Bravo: stricter quorum; Charlie: lower correlation threshold)
- **Governance Spec** (`docs/credibility-engine/GOVERNANCE_V0_9.md`): Policy engine, seal chaining, audit trail, drift recurrence, telemetry documentation

### Changed

- `pyproject.toml`: Version 0.8.0 → 0.9.0, added `governance*` to package discovery
- `credibility_engine/engine.py`: Policy evaluation in snapshot generation, drift registry updates, audit events
- `credibility_engine/packet.py`: Chained sealing with policy_hash + snapshot_hash, audit events on generate/seal
- `credibility_engine/api.py`: Policy/audit endpoints, quota enforcement, denied-attempt auditing
- `tenancy/__init__.py`: Export policy functions
- `dashboard/credibility-engine-demo/`: Policy hash + seal chain metadata display in packet preview
- `docs/credibility-engine/API_V0_8.md`: Added v0.9.0 endpoints note

### Stats

- 9 new files, 9 modified, v0.8.0 API compatibility preserved, abstract institutional modeling preserved

---

## [0.8.0] — 2026-02-19 — "Multi-Tenant Credibility Engine MVP"

### Added

- **Tenancy Module** (`tenancy/`): Tenant registry, path management, header-based RBAC
- **Tenant Boundary**: `tenant_id` propagation across claims, drift, snapshots, packets, seals
- **Tenant-Scoped Persistence**: Isolated data directories under `data/credibility/{tenant_id}/`
- **Tenant-Scoped API Routes**: Canonical `/api/{tenant_id}/credibility/*` endpoints
- **Backward-Compatible Alias Routes**: `/api/credibility/*` still serves default tenant
- **RBAC**: Header-based role enforcement (`X-Role`, `X-User`) — seal requires `coherence_steward`
- **Packet Generate/Seal Split**: Separate POST endpoints for generating (any role) and sealing (coherence_steward only)
- **Dashboard Tenant + Role Selectors**: Dropdown controls in API mode for tenant switching and role selection
- **Seed Data**: 3 demo tenants (alpha/bravo/charlie) with distinct credibility profiles
- **Tenant Registry**: `data/tenants.json` with 3 sample tenants auto-created on first use
- **Tenancy Spec** (`docs/credibility-engine/TENANCY_SPEC.md`): Tenant entity, roles, permission matrix, record schemas
- **API Reference** (`docs/credibility-engine/API_V0_8.md`): Complete v0.8.0 endpoint documentation

### Changed

- `pyproject.toml`: Version 0.7.0 → 0.8.0, added `tenancy*` to package discovery
- `credibility_engine/store.py`: Tenant-aware persistence with `tenant_id` parameter
- `credibility_engine/engine.py`: Tenant-scoped engine instances
- `credibility_engine/packet.py`: Generate/seal separation, tenant_id in packets
- `credibility_engine/api.py`: Per-tenant engine cache, tenant-scoped + alias routes
- `dashboard/credibility-engine-demo/`: Tenant and role selector UI in API mode

### Stats

- 10 new files, 10 modified, abstract institutional modeling preserved
- 3 demo tenants with isolated credibility profiles

---

## [0.7.0] — 2026-02-19 — "Real Credibility Engine Runtime"

### Added

- **Credibility Engine Runtime** (`credibility_engine/`): Real stateful engine module with live claim management, drift event processing, Credibility Index recalculation, and canonical artifact generation
- **JSONL Persistence** (`credibility_engine/store.py`): Append-only JSONL storage for claims, drift events, snapshots, correlation clusters, and sync regions under `data/credibility/`
- **API Endpoints** (`credibility_engine/api.py`): 6 FastAPI routes — `/api/credibility/snapshot`, `/claims/tier0`, `/drift/24h`, `/correlation`, `/sync`, `/packet`
- **Dashboard API Mode**: `DATA_MODE = "API"` toggle in `app.js` — dashboard can fetch from runtime API instead of static JSON files
- **Simulation-as-Driver**: `runner.py --mode engine` pushes simulation state into the runtime engine for persistence and API serving

### Changed

- `dashboard/api_server.py`: Integrated `credibility_engine.api` router
- `pyproject.toml`: Version 0.6.4 → 0.7.0, added `credibility_engine*` to package discovery
- `coherence_ops/__init__.py`: `__version__` 0.6.4 → 0.7.0

### Stats

- 8 new files, 7 modified, abstract institutional modeling preserved

---

## [0.6.4] — 2026-02-19 — "MDPT Beta Kit + Credibility Engine"

### Added

- **MDPT Index Generator** (`mdpt/tools/generate_prompt_index.py`): Reads PromptCapabilities CSV export, filters Approved rows, validates required fields, normalizes values, sorts deterministically, emits `prompt_index.json` + `prompt_index_summary.md` with Totals, Expiring Soon, Top Drift, Top Used sections
- **MDPT Prompt Index Schema** (`mdpt/templates/prompt_index_schema.json`): Draft-07 JSON Schema for the generated prompt index — nested capability model with links and telemetry
- **Product CLI** (`deepsigma/cli/`): Unified `deepsigma` entrypoint with 5 subcommands: `doctor`, `demo excel`, `validate boot`, `mdpt index`, `golden-path`
- **Power App Starter Kit** (`mdpt/powerapps/`): 8-screen builder guide + screen map + 6 PowerFx snippet files for canvas app construction in under 1 hour
- **Mermaid diagram** (`mermaid/37-mdpt-beta-kit.md`): MDPT Beta Kit lifecycle — Index → Catalog → Use → Log → Drift → Patch
- **Test fixtures**: `tests/fixtures/promptcapabilities_export.csv` — 8-row CSV fixture (6 Approved, 2 non-Approved) for MDPT Index Generator tests
- **CI gates**: MDPT Index generator validation + Product CLI smoke test

### Changed

- `pyproject.toml`: Version 0.6.3 → 0.6.4, `deepsigma` console script now points to `deepsigma.cli.main:main`, added `mdpt*` and `deepsigma*` to package discovery
- `coherence_ops/__init__.py`: `__version__` 0.6.3 → 0.6.4
- `.github/workflows/ci.yml`: Added MDPT Index generator + Product CLI smoke test gates
- `NAV.md`: Added MDPT Beta Kit section
- `README.md`: Added MDPT Beta Kit section with Product CLI and canonical Mermaid diagram

### Stats

- 27 new files, 6 modified, 29 new tests, 2 new CI gates

### Added — Credibility Engine & Scaled Truth Infrastructure

- **Credibility Index** (`docs/credibility-engine/credibility_index.md`): Composite 0–100 score from 6 components (tier-weighted claim integrity, drift penalty, correlation risk, quorum margin compression, TTL expiration, independent confirmation bonus). 5 interpretation bands (Stable → Compromised). Operational thresholds and fail-first indicators for 30k–40k node lattices
- **Core System Design** (`docs/credibility-engine/core_system_design.md`): Evidence node model (11 required fields), append-only event model (6 event types), TTL discipline (Tier 0–3), K-of-N quorum with correlation groups and Tier 0 out-of-band requirement
- **Sync Plane** (`docs/credibility-engine/sync_plane.md`): Event time vs ingest time, monotonic source sequence enforcement, independent time beacons, watermark logic, replay/backfill detection. Minimum: 3 regions, 3–5 sync nodes/region, 2 out-of-domain authorities, no region >40% authority
- **Drift-Patch-Seal loop** (`docs/credibility-engine/drift_patch_seal_loop.md`): 5 institutional drift categories (timing entropy, correlation drift, confidence volatility, TTL compression, external mismatch) mapping to 8 runtime drift types. Per-category: DS artifact → root cause → patch → MG diff → sealed episode
- **Deployment patterns** (`docs/credibility-engine/deployment_patterns.md`): MVP (6–8 engineers, $1.5M–$3M/year, Kafka/NATS + Neo4j/TerminusDB) + Production (30k–40k nodes, 3+ regions, hot/warm/cold, $6M–$10M/year) + economic modeling (~$170–$280/node/year)
- **Progressive lattice examples**: 01-mini-lattice (12 nodes, mechanics), 02-enterprise-lattice (~500 nodes, complexity), 03-credibility-engine-scale (30k–40k nodes, survivability) — abstract, non-domain
- **Mermaid diagrams**: 38-lattice-architecture (Claim → SubClaim → Evidence → Source + SyncPlane + Credibility Index), 39-drift-loop (institutional Drift → RootCause → Patch → MGUpdate → Seal → Index)

### Changed — Credibility Engine

- `README.md`: Added Progressive Escalation section and Credibility Engine section with category definition
- `NAV.md`: Added Credibility Engine section with 11 resource links, updated Diagrams count
- `mermaid/README.md`: Added diagrams 37–39 to catalogue

### Added — Credibility Engine Demo Cockpit

- **Demo Dashboard** (`dashboard/credibility-engine-demo/`): Static 7-panel cockpit surface — Credibility Index, Tier 0 claims, drift activity, correlation risk, TTL timeline, Sync Plane integrity, credibility packet generator. Vanilla HTML/CSS/JS, no frameworks. Mock JSON calibrated to 36,000-node production lattice
- `README.md`: Added demo link to Progressive Escalation section

### Added — Stage 2 Simulated Credibility Engine

- **Simulation Harness** (`sim/credibility-engine/`): Tick-based engine (2-second intervals, 15 sim-min/tick) that overwrites dashboard JSON atomically. Models: claims, correlation clusters, sync regions, drift fingerprints
- **4 Scenarios**: Day0 (stable baseline, CI 94–97), Day1 (entropy, CI 85–90), Day2 (coordinated darkness, CI 65–75), Day3 (external mismatch + recovery, CI 45–60)
- **Credibility Packet Generator**: Live DLR/RS/DS/MG summaries with narrative reasoning and sealed hash chain
- **Dashboard auto-refresh**: 2-second polling added to `app.js` for live simulation visualization
- **Hot-swap scenarios**: Drop `scenario.json` in dashboard directory to switch scenarios at runtime

### Stats (Credibility Engine addition)

- 11 new files + 11 demo files + 6 simulation files, 4 modified, 0 new tests (documentation-only), 2 new Mermaid diagrams

## [0.6.3] — 2026-02-19 — "Excel-first Hardening"

### Added

- **BOOT contract validator** (`tools/validate_workbook_boot.py`): CI gate enforcing BOOT!A1 metadata keys (version, ttl_hours_default, risk_lane_default, schema_ref, owner) + named table presence
- **Excel-first Money Demo** (`demos/excel_first/`): One-command deterministic Drift→Patch artifact loop — generates workbook, validates BOOT, detects drift, proposes patch, computes coherence delta
- **MDPT SharePoint build sheets**: List schemas for PromptCapabilities, PromptRuns, DriftPatches with column definitions, views, and relationship diagrams
- **MDPT Power Automate flows**: 4 flow recipes — drift alert, patch approval, weekly digest, workbook refresh validator
- **MDPT Power Apps screen map**: 5-screen canvas app layout (Home, Prompt Gallery, Run Detail, Drift Board, Patch Queue)
- **MDPT governance guide**: Permission model, audit trail, compliance considerations, escalation path
- **Test fixtures**: 4 `.xlsx` fixture workbooks for BOOT contract validation tests

### Changed

- `tools/generate_cds_workbook.py`: BOOT_TEXT now includes required metadata block with `BOOT!` prefix
- `.github/workflows/ci.yml`: Install `[excel]` extra, added BOOT contract validation + Excel-first Money Demo CI gates
- `pyproject.toml`: Version 0.6.2 → 0.6.3, added `excel-demo` console script
- `coherence_ops/__init__.py`: `__version__` 0.6.2 → 0.6.3

### Stats

- 20 new files, 10 modified, 27 new tests, 2 new CI gates

## [0.6.2] — 2026-02-19 — "Creative Director Suite"

### Added — Creative Director Suite (Excel-First Governance)

- **Dataset** (`datasets/creative_director_suite/`): 8 CSVs (25 rows each) — creative production sample data (Sanrio-themed campaigns)
- **Workbook generator** (`tools/generate_cds_workbook.py`): Produces governed Excel workbook with BOOT sheet + 7 named tables + 25 sample rows each
- **Template workbook** (`templates/creative_director_suite/Creative_Director_Suite_CoherenceOps_v2.xlsx`): Ready-to-use .xlsx for SharePoint deployment
- **Workbook Boot Protocol** (`docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md`): BOOT!A1 specification — LLM initialization via structured system prompt in cell A1
- **Table Schemas** (`docs/excel-first/TABLE_SCHEMAS.md`): 7 governance table schemas (tblTimeline, tblDeliverables, tblDLR, tblClaims, tblAssumptions, tblPatchLog, tblCanonGuardrails)
- **Multi-Dimensional Prompting for Teams** (`docs/excel-first/multi-dim-prompting-for-teams/README.md`): 6-lens prompt model (PRIME/EXEC/OPS/AI-TECH/HUMAN/ICON) with SharePoint-first architecture

### Changed

- `pyproject.toml`: Version 0.6.1 → 0.6.2, added `[excel]` optional dependency group (openpyxl)
- `coherence_ops/__init__.py`: `__version__` 0.5.0 → 0.6.2
- `README.md`: Added Creative Director Suite section with quickstart
- `NAV.md`: Added Excel-First Governance section

### Stats

- 17 new files, 5 modified, 200 CSV rows, 7 named tables, 1 generated workbook

## [0.6.1] — 2026-02-19 — "Interop Gateway"

### Added — Interoperability Stack

- **Interop Stack overview** (`docs/interop/README.md`): Unified architecture for AG-UI + A2A + MCP + Agora — one-stack view, layer-by-layer breakdown, Coherence Ops artifact mapping
- **Gateway Spec v0.1** (`docs/interop/COHERENCE_INTEROP_GATEWAY_SPEC_v0.1.md`): Protocol adapters, Agora-style negotiation engine, sealed contract lifecycle, runtime with retry/circuit breaker, observability (OTel trace propagation), drift sensor + patch loop, security controls, SLOs
- **ProtocolContract JSON Schema** (`schemas/interop/protocol_contract.schema.json`): Draft-07 schema with sealing, versioning, provenance, participants, message types, intents, error codes, constraints, signing + optional deprecation/migration/rollback/telemetry
- **Example contract** (`templates/interop/ProtocolContract.example.json`): Realistic AgentBooking ↔ AgentTravel interaction with 4 message types, 2 intents, 5 error codes
- **Drift triggers playbook** (`docs/interop/DRIFT_TRIGGERS.md`): 10 trigger types (schema, semantic, capability, policy, performance, freshness) with detection signals, severity, response actions, emitted artifacts
- **MVP plan** (`docs/interop/MVP_PLAN.md`): 14-day implementation plan with daily milestones, demo checkpoints, test coverage targets
- **Mermaid diagrams**: Interop request flow sequence (`mermaid/30-interop-request-flow.md`) + Agora negotiation flowchart (`mermaid/31-agora-negotiation-flow.md`)

### Fixed

- `TrustScorecardPanel.tsx`: Removed unused `React` import (TS6133)
- `expected_summary.json`: Updated golden-file drift count 5 → 6 to match pipeline output

### Stats

- 679 tests passing, 9 new files, 2 fixed, NAV.md updated

## [0.6.0] — 2026-02-18 — "Trust at Scale"

### Added — Connector Contract v1.0

- **ConnectorV1 Protocol** (`connectors/contract.py`): `@runtime_checkable` interface with `source_name`, `list_records()`, `get_record()`, `to_envelopes()`
- **RecordEnvelope** dataclass: Canonical wrapper with provenance, SHA-256 hashes, ACL tags, and raw payload
- **JSON Schema** (`specs/connector_envelope.schema.json`): Draft-07 schema for envelope validation
- **Normative spec** (`specs/connector_contract_v1.md`): Interface, pagination, retry/backoff, rate limiting, error model, auth handling
- **Connector compliance**: All 4 connectors (SharePoint, Dataverse, AskSage, Snowflake) implement `source_name` + `to_envelopes()`
- **Bridge function** `canonical_to_envelope()`: Converts existing canonical records to RecordEnvelope without breaking changes
- **30 contract tests** (`tests/test_connector_contract_v1.py`)

### Added — Connector Fixture Library

- **Deterministic fixtures** (`fixtures/connectors/`): `baseline_raw.json` + `delta_raw.json` for all 4 connectors (SharePoint, Dataverse, Snowflake, AskSage)
- **Golden envelopes** (`expected_envelopes.jsonl`): Pre-computed reference output for golden-file comparison
- **Fixture generator** (`tools/generate_connector_fixtures.py`): Reads raw fixtures, runs connector transforms, writes golden JSONL
- **24 fixture tests** (`tests/test_connector_fixtures.py`): Per-connector golden match, hash stability, cross-connector validation
- **Fixture docs** (`docs/fixtures.md`): Philosophy, structure, regeneration guide

### Added — Trust Scorecard

- **Metrics spec** (`specs/trust_scorecard_v1.md`): 14 metrics + 4 SLO thresholds (IRIS latency, steps passed, schema clean, score positive)
- **Scorecard generator** (`tools/trust_scorecard.py`): Reads Golden Path output, emits `trust_scorecard.json` with metrics + SLO checks
- **Dashboard panel** (`dashboard/src/TrustScorecardPanel.tsx`): Score cards, SLO badges, timing/quality metrics
- **API endpoint** (`dashboard/api_server.py`): `GET /api/trust_scorecard`
- **CI integration** (`.github/workflows/ci.yml`): Connector contract tests + scorecard generation steps
- **18 scorecard tests** (`tests/test_trust_scorecard.py`)

### Changed

- Dashboard App.tsx: Added Trust Scorecard tab (key 6), 7 views total
- NAV.md: Added Fixture Library and Trust & Metrics sections
- README.md: Added Trust Scorecard quickstart section
- pyproject.toml: Added `connectors*` to package discovery

### Stats

- 679 tests passing, 72 new tests, 27 new files, 9 modified

## [0.4.0] — 2026-02-18 — "Control Surface"

### Added — Tier 1: Persistence & Wiring

- **Memory Graph SQLite backend** (`coherence_ops/mg.py`): Optional `SQLiteBackend` for persistent MG storage across sessions
- **Automated drift detector** (`coherence_ops/ds.py`): `detect_signals()` generates drift events from sealed episodes by comparing telemetry against DTE thresholds
- **IRIS MCP tools** (`adapters/mcp/mcp_server_scaffold.py`): `iris.query` and `iris.reload` tools with lazy pipeline loading
- **Dashboard API server** (`dashboard/api_server.py`): FastAPI endpoints for episodes, drifts, agents, coherence, and IRIS queries

### Added — Tier 2: Enforcement & Observability

- **OpenTelemetry instrumentation** (`coherence_ops/otel.py`): Spans for IRIS queries, coherence scoring, MG operations; counters and histograms for query timing, episode throughput, drift severity
- **DTE Enforcer** (`engine/dte_enforcer.py`): Active constraint validation for Decision Timing Envelopes — deadline, stage budgets, feature TTL freshness, and limits
- **MCP resources & prompts**: `resources/list`, `resources/read`, `prompts/list`, `prompts/get` for operator workflows
- **Exhaust refiner hardening** (`coherence_ops/exhaust_refiner.py`): Entity typing for truth claims, confidence calibration with source-type weighting

### Added — Tier 3: Ecosystem & Dashboard

- **Dashboard SSE** (`dashboard/api_server.py`): `GET /api/sse` streaming endpoint multiplexing episodes, drifts, agents, and MG events; `GET /api/mg` Memory Graph JSON export
- **Zustand store** (`dashboard/src/store.ts`): Centralized state management replacing scattered `useState`
- **SSE hook** (`dashboard/src/hooks/useSSE.ts`): EventSource with auto-reconnect, HTTP polling fallback, mock data fallback
- **MG Graph view** (`dashboard/src/components/MGGraphView.tsx`): SVG-based Memory Graph visualization with node coloring by kind, click-to-inspect
- **LangGraph adapter** (`adapters/langgraph_exhaust.py`): Async `LangGraphExhaustTracker` for `astream_events()` with DTE constraint checking
- **Shared exhaust helpers** (`adapters/_exhaust_helpers.py`): Extracted common helpers for LangChain/LangGraph adapter reuse
- **Runtime schema validation** (`engine/schema_validator.py`): Lazy-compiled Draft 2020-12 validators with `$ref` resolution via `referencing.Registry`
- **Test infrastructure** (`tests/conftest.py`, `tests/test_benchmarks.py`, `tests/test_load.py`): Shared fixtures, performance benchmarks, 100-episode load test

### Changed

- Dashboard App.tsx rewired from `useState`/polling to Zustand + SSE; added MG Graph tab (key 5)
- LangChain adapter imports from shared `_exhaust_helpers` module (public API unchanged)
- Policy loader gained `validate_schema` parameter for opt-in JSON Schema validation
- CI now runs coverage gating and load test step
- MCP server version bumped to 0.4.0

### Stats

- 424 tests passing (up from 389), 17 new files, 9 modified

## [0.3.1] — 2026-02-17

### Fixed

- claim.schema.json: Removed Draft 4 exclusiveMinimum: false for Draft 2020-12 compatibility
- prime.py: Wired contested_claim_policy: "escalate" through to ESCALATE verdict
- test_schema_claim.py: Corrected claimId → claimIds assertion for canon schema

### Changed

- Added GitHub repository topics for discoverability

## [0.3.0] — 2026-02-16 — "Living Memory"

### Added — Money Demo (Drift → Patch in One Command)

- **Money Demo script** (`coherence_ops/examples/drift_patch_cycle.py`): One-command Drift → Patch loop producing 8 deterministic artifacts (3 reports, 3 MG snapshots, diff, Mermaid diagram)
- **CI contract gate**: Money Demo smoke test runs on every push to `main` and every PR (`.github/workflows/ci.yml`)
- **Coherence SLO definitions**: 8 enforceable SLOs aligned to Money Demo outputs (`metrics/coherence_slos.md`)
- **Smoke test suite**: 16 pytest tests covering artifacts, score monotonicity, diff integrity, and Mermaid output (`tests/test_money_demo.py`)
- **Evidence file**: `examples/demo-stack/MONEY_DEMO_EVIDENCE.md` with deterministic scores, artifact manifest, and contract checks
- **Issue #8 closeout**: `docs/issue_closeouts/issue_8_demo_loop.md`

### Changed

- `HERO_DEMO.md` — Added "Run the Money Demo" section with deterministic score output
- `metrics/coherence_slos.md` — Updated to v1.1.0 with Money Demo SLOs
- `coherence_ops/__init__.py` — Version bump to 0.3.0
- `pyproject.toml` — Version bump to 0.3.0

### Scores (Deterministic)

| State | Score | Grade |
|-------|-------|-------|
| Baseline | 90.00 | A |
| Drift | 85.75 | B |
| After Patch | 90.00 | A |

## [0.2.0] — 2026-02-15

### Added — Unified Atomic Claims

- **Claim Primitive v1.0**: `specs/claim.schema.json` — Universal Atomic Claim JSON Schema with confidence, status light, half-life, seal, graph edges, and provenance chain
- - **Claim-Native DLR v1.0**: `specs/dlr.schema.json` — Refactored Decision Lineage Record composing from claim references with rationale graph
  - - **Claim Primitive Example**: `llm_data_model/03_examples/claim_primitive_example.json` — SIGINT credential-stuffing scenario (CLAIM-2026-0001)
    - - **DLR Claim-Native Example**: `llm_data_model/03_examples/dlr_claim_native_example.json` — AccountQuarantine decision with 3 claims
      - - **Docs**: `docs/19-claim-primitive.md`, `docs/20-dlr-claim-native.md`
        - - **Wiki**: `wiki/Unified-Atomic-Claims.md` with sidebar navigation update
          - - **Mermaid Diagrams 27-28**: Claim Primitive (5 diagrams) and DLR Claim-Native (5 diagrams)
           
            - ### Added — RDF Semantic Layer Integration
           
            - - **OWL Ontology Module**: `rdf/ontology/claim_primitive.ttl` — 7 classes, 5 enumerations, 12 object properties, 25+ datatype properties under `ds:` namespace
              - - **SHACL Shapes**: `rdf/shapes/claim_primitive.shacl.ttl` — 6 node shapes enforcing JSON Schema constraints
                - - **Instance Graph**: `rdf/examples/claim_primitive_instance.ttl` — CLAIM-2026-0001 as RDF triples
                  - - **SPARQL Query Pack**: `rdf/queries/claim_queries.rq` — 10 queries (status light, triage, WHY, contradictions, expired half-lives, dependencies, supersession, truth type audit, classification, seal integrity)
                    - - **Framework Ontology**: 3 new `coh:Pattern` individuals in `rdf/coherence-ops-ontology.ttl` (ClaimPrimitive, ClaimNativeDLR, UnifiedAtomicClaims)
                     
                      - ### Added — New Schemas
                     
                      - - **Canon Schema**: `specs/canon.schema.json` — Promotes claim IDs from DLR to long-term blessed memory
                        - - **Drift Schema**: `specs/drift.schema.json` updated with claim-native drift detection
                          - - **Retcon Schema**: `specs/retcon.schema.json` — Retroactive claim correction operations
                            - - **Patch Schema**: `specs/patch.schema.json` — Patch operations on claim versions
                             
                              - ### Added — Code Integration
                             
                              - - **DLR Builder**: `coherence_ops/dlr.py` — `ClaimNativeDLRBuilder` class producing claim-native DLRs from sealed episodes
                                - - **Memory Graph**: `coherence_ops/mg.py` — `CLAIM` added as `NodeKind`, `add_claim()` method, claim-aware query support
                                  - - **IRIS Engine**: `coherence_ops/iris.py` — Full implementation wired to DLR/MG for WHY, WHAT_CHANGED, WHAT_DRIFTED, RECALL, STATUS resolution
                                   
                                    - ### Added — Tests
                                   
                                    - - **SHACL Validation Test**: `tests/test_shacl_claim.py` — Validates RDF instance against SHACL shapes
                                      - - **JSON Schema Validation Test**: `tests/test_schema_claim.py` — Validates JSON examples against JSON Schema specs
                                       
                                        - ### Changed
                                       
                                        - - `rdf/MANIFEST.md` — Added Claim Primitive section
                                          - - `rdf/README.md` — Added Claim Primitive documentation table
                                            - - `mermaid/README.md` — Added diagrams 27-28 to catalogue
                                              - - `wiki/_Sidebar.md` — Added Claim Schema, DLR Schema, Unified Atomic Claims links
                                                - - `coherence_ops/__init__.py` — Exports ClaimNativeDLRBuilder
                                                 
                                                  - ## [0.1.0] — 2026-02-13
                                                 
                                                  - ### Added
                                                 
                                                  - - **Engine**: supervisor scaffold, degrade ladder, policy loader
                                                    - - **Coherence Ops**: DLR builder, reflection session, drift signal collector, memory graph, auditor, scorer, reconciler, CLI (`coherence audit|score|mg|demo`)
                                                      - - **Verifiers**: read-after-write, invariant check stubs
                                                        - - **Specs**: JSON Schemas for Episode, DTE, Action Contract, Drift, Policy Pack
                                                          - - **Policy Packs**: versioned enforcement bundles with hash verification
                                                            - - **Tools**: `run_supervised.py`, `validate_examples.py`, `drift_to_patch.py`, `replay_episode.py`
                                                              - - **Adapters**: MCP JSON-RPC scaffold, OpenClaw skill runner scaffold, OTel exporter placeholder
                                                                - - **Dashboard**: interactive monitoring demo (HTML + React build)
                                                                  - - **LLM Data Model**: canonical record envelope, 6 record types, schemas, mappings, validation, retrieval, ontology
                                                                    - - **RDF Semantic Layer**: OWL ontology (Core 8 classes), SHACL shapes, SPARQL executive queries, SharePoint→RDF mappings
                                                                      - - **Mermaid Diagrams**: 26 diagrams covering architecture, runtime, schemas, coherence ops, LLM data model, and RDF layer
                                                                        - - **Examples**: demo-stack (4 scenarios), episodes, drift events, DTE packs, MCP samples
                                                                          - - **Docs**: 16 documentation files covering all modules
                                                                            - - **Wiki**: 48 pages covering concepts, schemas, integrations, governance, and visual documentation
                                                                             
                                                                              - ### Infrastructure
                                                                             
                                                                              - - **CI**: GitHub Actions with pytest (3.10/3.11/3.12), ruff lint, schema validation, and integration tests
                                                                                - - **Packaging**: `pyproject.toml` with console scripts (`overwatch`, `overwatch-validate`, `coherence`)
                                                                                  - - **Repo Governance**: SECURITY.md, CODEOWNERS, Dependabot, issue/PR templates, CONTRIBUTING.md
                                                                                    - - **Testing**: unit tests (degrade ladder, policy loader) + integration test (full coherence pipeline end-to-end: episode → seal → score → drift → audit → reconcile → patch → re-score)
                                                                                     
                                                                                      [0.4.0]: https://github.com/8ryanWh1t3/DeepSigma/compare/v0.1.0...v0.4.0
[0.2.0]: https://github.com/8ryanWh1t3/DeepSigma/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/8ryanWh1t3/DeepSigma/releases/tag/v0.1.0
