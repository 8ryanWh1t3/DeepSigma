# DeepSigma Feature Catalog

Machine source of truth: `release_kpis/feature_catalog.json`

## Categories

### Core Decision Engine
4D coherence scoring, decision log, drift detection, memory graph, reflection, reconciliation, PRIME gate, DTE enforcement, and IRIS operator queries.

- **4D Coherence Scorer** (`COHERENCE_SCORER`)
  - Computes unified 0-100 coherence score across policy adherence, outcome health, drift control, and memory completeness.
  - Artifacts: src/core/scoring.py
  - Enforcement: CI: coherence_ci.yml
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Coherence Gate** (`COHERENCE_GATE`)
  - Composable enforcement gate combining 4D scorer + PRIME gate to produce GREEN/YELLOW/RED signal.
  - Artifacts: src/core/coherence_gate.py
  - Enforcement: CI: coherence_ci.yml
  - KPI axes: Technical_Completeness, Authority_Modeling
- **Decision Log Record (DLR)** (`DECISION_LOG`)
  - Captures decision policy governance, action contracts used/blocked, verification requirements, and policy pack stamps.
  - Artifacts: src/core/decision_log.py
  - Enforcement: CI: ci.yml
  - KPI axes: Technical_Completeness, Authority_Modeling
- **Drift Signal Collector** (`DRIFT_SIGNAL`)
  - Ingests and organizes drift events by type, severity, fingerprint, and recurrence; feeds audit loop and scoring.
  - Artifacts: src/core/drift_signal.py
  - Enforcement: CI: ci.yml
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Memory Graph (MG)** (`MEMORY_GRAPH`)
  - Provenance and recall graph storing episodes, actions, drift fingerprints, patches, and claims with sub-60s retrieval.
  - Artifacts: src/core/memory_graph.py, src/core/memory_graph_backends.py
  - Enforcement: CI: ci.yml
  - KPI axes: Technical_Completeness, Data_Integration
- **Reflection Session (RS)** (`REFLECTION`)
  - Aggregates sealed episodes into learning summaries: outcome distribution, degradation frequency, verification pass rates.
  - Artifacts: src/core/reflection.py
  - Enforcement: CI: ci.yml
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Cross-Artifact Reconciler** (`RECONCILER`)
  - Detects and proposes repairs for inconsistencies between DLR, drift signals, memory graph, and reflection summaries.
  - Artifacts: src/core/reconciler.py
  - Enforcement: CI: ci.yml
  - KPI axes: Technical_Completeness, Operational_Maturity
- **PRIME Threshold Gate** (`PRIME_GATE`)
  - Converts LLM probability gradients into APPROVE/DEFER/ESCALATE verdicts using Truth-Reasoning-Memory invariants.
  - Artifacts: src/core/prime.py
  - Enforcement: CI: ci.yml
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Decision Timing Envelope (DTE)** (`DTE_ENFORCER`)
  - Validates hard timing constraints: deadline, stage budgets, feature TTL, hop/tool call limits.
  - Artifacts: src/core/dte_enforcer.py
  - Enforcement: CI: ci.yml
  - KPI axes: Operational_Maturity, Automation_Depth
- **IRIS Operator Query Engine** (`IRIS`)
  - Resolves WHY/WHAT_CHANGED/WHAT_DRIFTED/RECALL/STATUS queries by walking MG claim topology and DLR rationale graph in <60s.
  - Artifacts: src/core/iris.py
  - Enforcement: CI: ci.yml
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Coherence Auditor** (`COHERENCE_AUDIT`)
  - Periodic cross-artifact consistency checks detecting orphan drift, missing episodes, policy stamp mismatches.
  - Artifacts: src/core/audit.py
  - Enforcement: CI: ci.yml
  - KPI axes: Operational_Maturity, Technical_Completeness

### FEEDS Event Surface
Federated Event Envelope Distribution Surface — event-driven pub/sub connecting governance primitives (TS, ALS, DLR, DS, CE) via file-based bus with manifest-first ingest, deterministic drift detection, authority validation, triage state machine, and canon versioning.

- **Event Envelope + Schemas** (`FEEDS_ENVELOPE`)
  - Canonical event envelope with 6 topic-specific payload schemas, SHA-256 payload hashing, two-phase validation (envelope then payload), and golden fixtures.
  - Artifacts: src/core/feeds/types.py, src/core/feeds/envelope.py, src/core/feeds/validate.py, src/core/schemas/feeds/feeds_event_envelope.schema.json, src/core/schemas/feeds/truth_snapshot.schema.json, src/core/schemas/feeds/authority_slice.schema.json, src/core/schemas/feeds/decision_lineage.schema.json, src/core/schemas/feeds/drift_signal.schema.json, src/core/schemas/feeds/canon_entry.schema.json, src/core/schemas/feeds/packet_index.schema.json
  - Enforcement: CI: coherence_ci.yml, make validate-feeds
  - KPI axes: Technical_Completeness, Automation_Depth
- **File-Bus Pub/Sub + DLQ** (`FEEDS_BUS`)
  - Atomic file-based publisher (temp+rename), poll-based subscriber with claim lifecycle (inbox→processing→ack), dead-letter queue with replay, and multi-worker safety via rename semantics.
  - Artifacts: src/core/feeds/bus/publisher.py, src/core/feeds/bus/subscriber.py, src/core/feeds/bus/dlq.py, src/core/feeds/bus/__init__.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-bus
  - KPI axes: Data_Integration, Operational_Maturity
- **Manifest-First Ingest Orchestrator** (`FEEDS_INGEST`)
  - All-or-none packet ingest: manifest verification, SHA-256 hash checks, schema validation, per-topic extraction, atomic staging, and PROCESS_GAP drift emission on failure.
  - Artifacts: src/core/feeds/ingest/orchestrator.py, src/core/feeds/ingest/extractors.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-ingest
  - KPI axes: Data_Integration, Technical_Completeness
- **Authority Gate Consumer** (`FEEDS_AUTHORITY_GATE`)
  - Compares DLR action claims against ALS blessed claims; emits AUTHORITY_MISMATCH drift signal when unblessed claims detected.
  - Artifacts: src/core/feeds/consumers/authority_gate.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-consumers
  - KPI axes: Authority_Modeling, Operational_Maturity
- **Evidence Completeness Consumer** (`FEEDS_EVIDENCE_CHECK`)
  - Cross-references DLR evidence refs against packet_index manifest; emits PROCESS_GAP drift signal on missing refs.
  - Artifacts: src/core/feeds/consumers/evidence_check.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-consumers
  - KPI axes: Operational_Maturity, Technical_Completeness
- **Drift Triage State Machine** (`FEEDS_TRIAGE`)
  - SQLite-backed drift triage with enforced state transitions (NEW→TRIAGED→PATCH_PLANNED→PATCHED→VERIFIED), severity tracking, recurrence fingerprinting, and operator CLI.
  - Artifacts: src/core/feeds/consumers/triage.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-consumers
  - KPI axes: Operational_Maturity, Automation_Depth
- **Canon Store** (`FEEDS_CANON_STORE`)
  - Append-only SQLite canon store with semantic versioning, supersedes chain, domain filtering, version chain traversal, and cache invalidation event emission.
  - Artifacts: src/core/feeds/canon/store.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-canon
  - KPI axes: Authority_Modeling, Data_Integration
- **Claim Validator** (`FEEDS_CLAIM_VALIDATOR`)
  - Validates claims for contradictions (via graph.contradicts), TTL expiry (halfLife + timestampCreated), and confidence/statusLight consistency; emits drift signals on issues.
  - Artifacts: src/core/feeds/canon/claim_validator.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-canon
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Memory Graph Writer** (`FEEDS_MG_WRITER`)
  - Idempotent per-packet JSON graph writer with typed nodes (by topic) and edges (packet_contains, ds_detected_from, ce_resolves, als_authorizes).
  - Artifacts: src/core/feeds/canon/mg_writer.py
  - Enforcement: CI: coherence_ci.yml, make test-feeds-canon
  - KPI axes: Data_Integration, Technical_Completeness

### Deterministic Governance Boundary
Governance enforced before execution: default deny, halt on ambiguity, proof-first artifacts.

- **Pre-Execution Gate** (`PRE_EXEC_GATE`)
  - Blocks execution unless intent+authority+policy requirements are satisfied.
  - Artifacts: runs/intent_packet.json, runs/authority_contract.json, runs/input_snapshot.json
  - Enforcement: scripts/pre_exec_gate.py, make milestone-gate, CI: kpi_gate.yml
  - KPI axes: Automation_Depth, Authority_Modeling, Operational_Maturity
- **Default Deny** (`DEFAULT_DENY`)
  - If required conditions cannot be evaluated or are missing, execution is denied.
  - Artifacts: governance/ambiguity_policy.md
  - Enforcement: scripts/pre_exec_gate.py
  - KPI axes: Authority_Modeling, Operational_Maturity
- **Halt on Ambiguity** (`HALT_ON_AMBIGUITY`)
  - Conflicts/unknowns/insufficient provenance trigger a hard fail before routing.
  - Artifacts: governance/ambiguity_policy.md
  - Enforcement: scripts/pre_exec_gate.py, scripts/validate_v2_1_0_milestone.py
  - KPI axes: Authority_Modeling, Operational_Maturity

### Intent Capture & Governance
Intent declared pre-action and bound to execution.

- **Intent Packet Schema** (`INTENT_PACKET_SCHEMA`)
  - Formal structure for intent, scope, success criteria, TTL, author, authority.
  - Artifacts: schemas/intent_packet.schema.json, runs/intent_packet.json
  - Enforcement: scripts/validate_intent_packet.py, scripts/validate_v2_1_0_milestone.py
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Intent TTL Enforcement** (`INTENT_TTL`)
  - Intent expires; expired intent blocks execution.
  - Artifacts: runs/intent_packet.json
  - Enforcement: scripts/validate_intent_packet.py
  - KPI axes: Operational_Maturity, Authority_Modeling
- **Intent Hash Binding** (`INTENT_HASH_BINDING`)
  - Intent hash is bound into proof chain and audit pack.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/crypto_proof.py
  - KPI axes: Technical_Completeness, Authority_Modeling

### Audit-Neutral Decision Logic
Claim→Evidence→Authority binding and context-free audit export.

- **Decision Invariants Ledger** (`DECISION_INVARIANTS`)
  - Rules: claim→evidence required, no overwrite, authority precedence, TTL/half-life.
  - Artifacts: governance/decision_invariants.md
  - Enforcement: scripts/validate_v2_1_0_milestone.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Claim→Evidence→Authority Validator** (`CEA_VALIDATOR`)
  - Machine-checkable binding of claims, evidence, and authority references.
  - Artifacts: runs/decision_record.json
  - Enforcement: scripts/validate_claim_evidence_authority.py
  - KPI axes: Technical_Completeness, Enterprise_Readiness
- **Audit-Neutral Export Pack** (`AUDIT_NEUTRAL_PACK`)
  - Exports sealed facts + hashes + authority + proof bundle without political narrative.
  - Artifacts: packs/audit_neutral/*
  - Enforcement: scripts/export_audit_neutral_pack.py
  - KPI axes: Enterprise_Readiness, Operational_Maturity

### Deterministic Replay & Proof Chain
Hash chain, signature verification, Merkle commitments, authority ledger, and deterministic replay.

- **Sealed Input Snapshot** (`INPUT_SNAPSHOT`)
  - Inputs captured and hashed for deterministic evidence.
  - Artifacts: runs/input_snapshot.json
  - Enforcement: scripts/capture_run_snapshot.py
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Proof Bundle** (`PROOF_BUNDLE`)
  - Hash chain across intent, snapshot, authority contract, outputs; optional signature verify.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/crypto_proof.py
  - KPI axes: Technical_Completeness, Authority_Modeling
- **Replay Validation** (`REPLAY_VALIDATION`)
  - Validates proof chain presence and readiness for deterministic replay.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/replay_run.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Authority Ledger** (`AUTHORITY_LEDGER`)
  - Append-only ledger of authority actions (key rotations, approvals) with NDJSON persistence and integrity verification.
  - Artifacts: artifacts/authority_ledger/ledger.ndjson
  - Enforcement: scripts/export_authority_ledger.py, scripts/verify_authority_signature.py
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **Idempotency Guard** (`IDEMPOTENCY_GUARD`)
  - Prevents duplicate execution of already-sealed runs by checking proof chain hashes.
  - Artifacts: runs/proof_bundle.json
  - Enforcement: scripts/idempotency_guard.py
  - KPI axes: Operational_Maturity, Technical_Completeness

### Security & Key Management
Rotatable keyring, multi-cloud KMS, re-encryption at rest, authority ledger, crypto policy enforcement.

- **Rotatable Keyring** (`KEYRING`)
  - File-backed key management with version records, TTL/status lifecycle, and rotation history.
  - Artifacts: src/deepsigma/security/keyring.py
  - Enforcement: CI: signature_gate.yml
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **Multi-Cloud KMS** (`KMS_PROVIDERS`)
  - KMS provider abstraction supporting AWS KMS, Azure Key Vault, GCP KMS, and local keyring.
  - Artifacts: src/deepsigma/security/providers/
  - Enforcement: CI: signature_gate.yml
  - KPI axes: Enterprise_Readiness, Scalability
- **Re-encryption at Rest** (`REENCRYPT`)
  - Batch re-encryption of evidence with checkpoint/resume support and performance benchmarking.
  - Artifacts: src/deepsigma/security/reencrypt.py, scripts/reencrypt_benchmark.py
  - Enforcement: CI: reencrypt_benchmark.yml
  - KPI axes: Scalability, Enterprise_Readiness
- **Crypto Policy Enforcement** (`CRYPTO_POLICY`)
  - Runtime crypto policy loading with ENV override support; blocks execution on policy violations.
  - Artifacts: src/deepsigma/security/policy.py, governance/crypto_policy.yaml
  - Enforcement: scripts/crypto_misuse_scan.py, CI: signature_gate.yml
  - KPI axes: Authority_Modeling, Technical_Completeness

### Connector & Integration Framework
ConnectorV1 protocol, LLM framework adapters, enterprise SaaS connectors, MCP server, OpenTelemetry.

- **ConnectorV1 Protocol** (`CONNECTOR_CONTRACT`)
  - Standard interface + RecordEnvelope dataclass for all connectors; defines provenance, hashes, metadata wrapping.
  - Artifacts: src/adapters/contract.py, schemas/core/connector_contract_v1.md
  - Enforcement: tests-enterprise/
  - KPI axes: Data_Integration, Technical_Completeness
- **LLM Framework Adapters** (`LLM_ADAPTERS`)
  - Exhaust + governance callbacks for LangChain, LangGraph, Anthropic, Azure OpenAI, and local LLM.
  - Artifacts: src/adapters/langchain_exhaust.py, src/adapters/langchain_governance.py, src/adapters/anthropic_exhaust.py, src/adapters/azure_openai_exhaust.py, src/adapters/local_llm/
  - Enforcement: tests-enterprise/
  - KPI axes: Data_Integration, Enterprise_Readiness
- **Enterprise SaaS Connectors** (`SAAS_CONNECTORS`)
  - SharePoint, Snowflake (Cortex AI + warehouse + exhaust), Power Platform, and AskSage connectors.
  - Artifacts: src/adapters/sharepoint/, src/adapters/snowflake/, src/adapters/powerplatform/, src/adapters/asksage/
  - Enforcement: tests-enterprise/
  - KPI axes: Data_Integration, Scalability
- **Model Context Protocol Server** (`MCP_SERVER`)
  - MCP server scaffold exposing tools and prompts to AI agents with resilience and backoff handling.
  - Artifacts: src/adapters/mcp/mcp_server_scaffold.py, src/adapters/mcp/resilience.py
  - Enforcement: CI: docker-mcp.yml
  - KPI axes: Data_Integration, Enterprise_Readiness
- **OpenTelemetry Integration** (`OTEL`)
  - OTEL exporter, sidecar injection, and span utilities for observability backends (Jaeger, Datadog).
  - Artifacts: src/adapters/otel/otel_exporter.py, src/adapters/otel/sidecar.py
  - Enforcement: CI: docker-otel.yml
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **OpenClaw Policy Adapter** (`OPENCLAW`)
  - Institutional control flow adapter with OVERWATCH-compatible wrapper for policy-driven routing.
  - Artifacts: src/adapters/openclaw/adapter.py, src/adapters/openclaw/runtime.py
  - Enforcement: tests-enterprise/
  - KPI axes: Authority_Modeling, Enterprise_Readiness

### Credibility Engine
Tenant-scoped credibility computation, tiering, packet sealing, and FastAPI endpoints.

- **Credibility Computation** (`CREDIBILITY_COMPUTE`)
  - Core credibility scoring engine with tier classification and packet sealing.
  - Artifacts: src/credibility_engine/engine.py, src/credibility_engine/tiering.py, src/credibility_engine/packet.py
  - Enforcement: tests-enterprise/
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Credibility API** (`CREDIBILITY_API`)
  - FastAPI routes for tenant-scoped credibility, policy, and audit endpoints with quota enforcement.
  - Artifacts: src/credibility_engine/api.py
  - Enforcement: tests-enterprise/
  - KPI axes: Enterprise_Readiness, Scalability

### Mesh Federation
Multi-region federated quorum, anti-entropy, sync plane, and WAN partition-safe consensus.

- **Federated Quorum** (`FEDERATION`)
  - Multi-region quorum + correlation computation; partitions yield UNKNOWN (safe default).
  - Artifacts: src/mesh/federation.py, src/mesh/sync_plane.py
  - Enforcement: tests-enterprise/
  - KPI axes: Scalability, Operational_Maturity
- **Anti-Entropy Protocol** (`ANTI_ENTROPY`)
  - Consistency healing across mesh nodes with node discovery, log store, and transport abstraction.
  - Artifacts: src/mesh/anti_entropy.py, src/mesh/discovery.py, src/mesh/logstore.py
  - Enforcement: tests-enterprise/
  - KPI axes: Scalability, Technical_Completeness

### Multi-Tenancy
Tenant registry, RBAC, isolated paths, per-tenant policy enforcement, and immutable audit trails.

- **Tenant Isolation** (`TENANT_ISOLATION`)
  - Tenant registry with isolated file paths, per-tenant RBAC, and policy enforcement.
  - Artifacts: src/tenancy/tenants.py, src/tenancy/rbac.py, src/tenancy/paths.py
  - Enforcement: tests-enterprise/
  - KPI axes: Enterprise_Readiness, Authority_Modeling
- **Immutable Audit Trail** (`GOVERNANCE_AUDIT`)
  - Append-only audit logs per tenant with governance telemetry and quota enforcement.
  - Artifacts: src/governance/audit.py, src/governance/telemetry.py
  - Enforcement: tests-enterprise/
  - KPI axes: Enterprise_Readiness, Operational_Maturity

### Repo Radar KPI System
8 KPI axes, telemetry-driven scoring, eligibility tiers, confidence bands, radar/trend rendering, composite history, issue-driven deltas, and automated gate enforcement.

- **KPI Run Pipeline** (`KPI_RUN`)
  - Full orchestration: compute, merge, render radar/badge/trend/composite, gate, stability, TEC, and PR comment.
  - Artifacts: release_kpis/radar_*.png, release_kpis/badge_latest.svg, release_kpis/PR_COMMENT.md
  - Enforcement: CI: kpi.yml, CI: kpi_gate.yml
  - KPI axes: All
- **KPI Gate Enforcement** (`KPI_GATE`)
  - Floor validation and max-drop regression detection across all 8 KPI dimensions.
  - Artifacts: release_kpis/KPI_GATE_REPORT.md, governance/kpi_spec.yaml
  - Enforcement: scripts/kpi_gate.py, CI: kpi_gate.yml
  - KPI axes: Automation_Depth, Operational_Maturity
- **Evidence Eligibility Tiers** (`KPI_ELIGIBILITY`)
  - KPI values capped by evidence level: unverified (3.0), simulated (6.0), real (8.5), production (10.0).
  - Artifacts: governance/kpi_eligibility.json, release_kpis/kpi_confidence.json
  - Enforcement: scripts/kpi_merge.py
  - KPI axes: All
- **Confidence Bands** (`KPI_CONFIDENCE`)
  - Statistical confidence intervals around each KPI with low/high bounds per version.
  - Artifacts: release_kpis/kpi_bands_*.json
  - Enforcement: scripts/kpi_confidence_bands.py
  - KPI axes: All
- **Issue-Driven KPI Deltas** (`KPI_ISSUES`)
  - Derives KPI credit/debt from GitHub issues with P0-P3 severity scoring and label-based mapping.
  - Artifacts: release_kpis/issue_deltas.json, governance/kpi_issue_map.yaml
  - Enforcement: scripts/kpi_from_issues.py, scripts/issue_label_gate.py
  - KPI axes: Automation_Depth, Operational_Maturity
- **Composite Radar + Trend** (`COMPOSITE_RADAR`)
  - Multi-version radar overlay and historical trend chart showing KPI trajectory.
  - Artifacts: release_kpis/radar_composite_latest.png, release_kpis/kpi_trend.png
  - Enforcement: scripts/render_composite_radar.py, scripts/render_kpi_trend.py
  - KPI axes: All
- **Layer Coverage Injection** (`LAYER_COVERAGE`)
  - Appends Decision Infrastructure layer→KPI mapping into PR comment.
  - Artifacts: release_kpis/layer_kpi_mapping.json, release_kpis/PR_COMMENT.md
  - Enforcement: scripts/kpi_run.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness

### Health & Stability Monitoring
ICR/PCR/TEC health watchers, nonlinear stability analysis, roadmap forecasting, and pulse insights.

- **Infrastructure Coherence Ratio (ICR)** (`ICR_HEALTH`)
  - Monitors infrastructure coherence metrics with snapshot history and GitHub-sourced data.
  - Artifacts: release_kpis/health/icr_latest.json
  - Enforcement: scripts/icr_health_watcher.py, make health-v2
  - KPI axes: Operational_Maturity, Technical_Completeness
- **PR Complexity Ratio (PCR)** (`PCR_HEALTH`)
  - Tracks pull request complexity trends with snapshot history.
  - Artifacts: release_kpis/health/pcr_latest.json
  - Enforcement: scripts/pr_complexity_watcher.py, make health-v2
  - KPI axes: Operational_Maturity, Automation_Depth
- **Health Summary + X-Ray** (`HEALTH_SUMMARY`)
  - Aggregates ICR/PCR/TEC health into unified summary with X-ray health block.
  - Artifacts: release_kpis/health/HEALTH_SUMMARY.md, release_kpis/health/xray_health_block.md
  - Enforcement: scripts/health_summary.py, make health-v2
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Nonlinear Stability Analysis** (`STABILITY`)
  - SSI computation, Monte Carlo simulation, adjusted forecasting, and stability report generation.
  - Artifacts: release_kpis/stability_*.json, release_kpis/nonlinear_stability_report.md
  - Enforcement: scripts/nonlinear_stability.py, make stability
  - KPI axes: Operational_Maturity, Economic_Measurability
- **Roadmap Intelligence** (`ROADMAP`)
  - Roadmap forecasting, badge rendering, timeline visualization, and scope gate validation.
  - Artifacts: release_kpis/roadmap_forecast.json, release_kpis/roadmap_badge.svg, release_kpis/roadmap_timeline.svg
  - Enforcement: scripts/roadmap_forecast.py, scripts/roadmap_scope_gate.py, CI: roadmap_guard.yml
  - KPI axes: Enterprise_Readiness, Operational_Maturity
- **Pulse Insights** (`PULSE_INSIGHTS`)
  - Collects operational insight signals and scores for KPI telemetry enrichment.
  - Artifacts: release_kpis/insights_metrics.json
  - Enforcement: scripts/pulse_insights.py, make pulse-insights
  - KPI axes: Operational_Maturity, Data_Integration

### Economic Measurability (TEC / C-TEC)
Time/Effort/Cost modeling with complexity-adjusted variants, 3-tier audience outputs, and daily snapshots.

- **TEC / C-TEC Engine** (`TEC_CTEC`)
  - Complexity-adjusted effort/cost estimation producing internal, executive, and fully-burdened audience variants.
  - Artifacts: release_kpis/tec_internal.json, release_kpis/tec_executive.json, release_kpis/tec_dod.json, release_kpis/TEC_SUMMARY.md
  - Enforcement: scripts/tec_ctec.py, make tec
  - KPI axes: Economic_Measurability
- **TEC Health Snapshots** (`TEC_SNAPSHOTS`)
  - Daily TEC snapshots with historical tracking for trend analysis.
  - Artifacts: release_kpis/health/history/TEC_SNAPSHOT_*.json, release_kpis/health/tec_ctec_latest.json
  - Enforcement: scripts/tec_ctec.py --snapshot
  - KPI axes: Economic_Measurability, Operational_Maturity

### Pilot & Operator Readiness
Pilot-in-a-box deployment, 60-second challenge, pilot pack generation, and project intake.

- **Pilot-in-a-Box** (`PILOT_IN_A_BOX`)
  - Self-contained pilot deployment script for rapid evaluation environments.
  - Artifacts: scripts/pilot_in_a_box.py
  - Enforcement: tests-enterprise/
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **Why 60s Challenge** (`WHY_60S`)
  - Validates that key operator queries resolve within 60-second target.
  - Artifacts: scripts/why_60s_challenge.py
  - Enforcement: tests-enterprise/
  - KPI axes: Operational_Maturity
- **Pilot Pack Generator** (`PILOT_PACK`)
  - Generates deployment-ready pilot pack with configuration, docs, and evaluation criteria.
  - Artifacts: pilot_pack/**
  - Enforcement: scripts/pilot_pack.py
  - KPI axes: Enterprise_Readiness, Operational_Maturity
- **Project Intake** (`PROJECT_INTAKE`)
  - Structured intake workflow for new pilot projects with scoring and routing.
  - Artifacts: scripts/project_intake.py
  - Enforcement: tests-enterprise/
  - KPI axes: Enterprise_Readiness

### Container Infrastructure
Docker images for coherence, exhaust, MCP, tools, and OTEL workloads with CI validation.

- **Docker Image Suite** (`DOCKER_IMAGES`)
  - Containerized workloads: coherence engine, exhaust pipeline, MCP server, tools, and OTEL sidecar.
  - Artifacts: docker/Dockerfile.coherence, docker/Dockerfile.exhaust, docker/Dockerfile.mcp, docker/Dockerfile.tools
  - Enforcement: CI: docker-coherence.yml, CI: docker-exhaust.yml, CI: docker-mcp.yml, CI: docker-tools.yml, CI: docker-otel.yml
  - KPI axes: Enterprise_Readiness, Scalability

## Outer-Edge Boundaries

- Not claiming full jurisdictional policy packs (EU AI Act article-by-article enforcement) yet
- Not claiming full cryptographic attestation across all pipelines and connectors yet
- Not claiming a full runtime control plane is governance (runtime is subordinate)
- Mesh federation is functional but not yet tested at production-scale WAN partitions
- Credibility engine API is tenant-scoped but not yet load-tested at multi-thousand-tenant scale
