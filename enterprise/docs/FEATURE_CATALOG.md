# DeepSigma Feature Catalog

**Version:** 2.1.0
**Last updated:** 2026-02-28

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
- **Authority Chain Verification** (`AUTHORITY_CHAIN_VERIFY`)
  - Verifies SHA-256 hash chain integrity across all authority ledger entries via `verify_chain`; detects tampered or missing entries.
  - Artifacts: src/core/authority.py
  - Enforcement: tests/test_agent.py, CI: ci.yml
  - KPI axes: Authority_Modeling, Technical_Completeness
  - Added: v2.1.0 (#469)
- **Replay Detection** (`REPLAY_DETECTION`)
  - Detects duplicate authority grant/revoke attempts via `detect_replay` using entry fingerprinting; prevents replay attacks on the authority ledger.
  - Artifacts: src/core/authority.py
  - Enforcement: tests/test_agent.py, CI: ci.yml
  - KPI axes: Authority_Modeling, Operational_Maturity
  - Added: v2.1.0 (#470)
- **Evidence Source Binding** (`EVIDENCE_SOURCE_BINDING`)
  - Schema and validator binding evidence artifacts to their originating source with provenance metadata and hash verification.
  - Artifacts: src/core/authority.py, schemas/evidence_source_binding.schema.json
  - Enforcement: tests/test_agent.py, CI: ci.yml
  - KPI axes: Technical_Completeness, Enterprise_Readiness
  - Added: v2.1.0 (#472)
- **Economic Cost Ledger** (`ECONOMIC_COST_LEDGER`)
  - Per-decision cost tracking with drift-to-patch value ratio, linking remediation costs to governance outcomes.
  - Artifacts: release_kpis/economic_metrics.json
  - Enforcement: scripts/economic_metrics.py, CI: kpi.yml
  - KPI axes: Economic_Measurability, Operational_Maturity
  - Added: v2.1.0 (#473)
- **Intent Mutation Detection** (`INTENT_MUTATION_DETECT`)
  - Detects intent drift between sealed runs by comparing intent packet hashes across episodes; flags mutations as governance violations.
  - Artifacts: src/core/cli.py, src/core/agent.py
  - Enforcement: tests/test_agent.py, CI: ci.yml
  - KPI axes: Authority_Modeling, Operational_Maturity
  - Added: v2.1.0 (#474)
- **Schema Version Enforcement** (`SCHEMA_VERSION_ENFORCE`)
  - CI gate enforcing schema version parity across all governance artifacts; blocks releases with mismatched schema versions.
  - Artifacts: scripts/validate_v2_1_0_milestone.py
  - Enforcement: CI: ci.yml, CI: kpi_gate.yml
  - KPI axes: Automation_Depth, Technical_Completeness
  - Added: v2.1.0 (#475)

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
- **Security Proof Pack v2** (`SECURITY_PROOF_PACK`)
  - Integrity-chain-aware security proof: key lifecycle verification (generation/rotation/revocation), crypto proof validation, seal chain integrity, contract fingerprint consistency.
  - Artifacts: release_kpis/security_proof_pack.json, release_kpis/SECURITY_GATE_REPORT.md
  - Enforcement: scripts/security_proof_pack.py, make security-gate, CI: security_gate.yml
  - KPI axes: Operational_Maturity, Authority_Modeling

- **Authority Custody** (`AUTHORITY_CUSTODY`)
  - Production signature key custody: generation, rotation (90-day), revocation, and verification path with signing_key_id tracking in authority ledger entries.
  - Artifacts: docs/docs/security/KEY_CUSTODY.md, governance/security_crypto_policy.json
  - Enforcement: tests/test_authority_signature_custody.py
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **Refusal Contract** (`REFUSAL_CONTRACT`)
  - Explicit refusal authority: REFUSE action type in action contracts, AUTHORITY_REFUSAL ledger entries, and AUTHORITY_REFUSED drift signal emission in authority gate consumer.
  - Artifacts: src/deepsigma/security/action_contract.py, src/deepsigma/security/authority_ledger.py, src/core/feeds/consumers/authority_gate.py
  - Enforcement: tests/test_authority_refusal.py
  - KPI axes: Authority_Modeling, Operational_Maturity
- **Authority Evidence Export** (`AUTHORITY_EVIDENCE`)
  - Release artifact exporting authority evidence chain: ledger entries, chain verification, grant/refusal counts, signing key IDs, and verification hash.
  - Artifacts: release_kpis/authority_evidence.json
  - Enforcement: scripts/export_authority_evidence.py, make authority-evidence
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **Economic Metrics** (`ECONOMIC_METRICS`)
  - Dedicated economic evidence artifact sourced from TEC pipeline + security benchmarks. Provides kpi_eligible=true + evidence_level=real_workload to uncap economic_measurability KPI.
  - Artifacts: release_kpis/economic_metrics.json, schemas/economic_metrics_v1.json
  - Enforcement: scripts/economic_metrics.py, make economic-metrics
  - KPI axes: Economic_Measurability

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
- **Tool-Call / LLM Span Tracing** (`OTEL_TOOL_SPANS`)
  - Per-tool-call and per-LLM-completion child spans with token counters and latency histograms. Registered in span registry with CI gate enforcement.
  - Artifacts: src/adapters/otel/exporter.py, src/adapters/otel/spans.py
  - Enforcement: tests/test_otel_span_registry.py, CI: ci.yml
  - KPI axes: Operational_Maturity, Enterprise_Readiness
  - Added: v2.1.0
- **Connector Auto-Instrumentation** (`OTEL_INSTRUMENTATION`)
  - `@traced` decorator and `InstrumentedConnector` mixin wrapping adapter methods with OTel spans. W3C `traceparent` inject/extract for cross-service propagation.
  - Artifacts: src/adapters/otel/instrumentation.py
  - Enforcement: CI: ci.yml
  - KPI axes: Operational_Maturity, Data_Integration
  - Added: v2.1.0
- **Runtime Gate** (`RUNTIME_GATE`)
  - Composable pre-execution policy constraint evaluator with 5 gate types (freshness, verification, latency_slo, quota, custom expr). SLO circuit breaker trips on sustained metric breach.
  - Artifacts: src/engine/runtime_gate.py
  - Enforcement: CI: ci.yml
  - KPI axes: Automation_Depth, Authority_Modeling
  - Added: v2.1.0
- **Encryption at Rest** (`ENCRYPTION_AT_REST`)
  - Fernet (AES-128-CBC + HMAC-SHA256) file-level encryption for sealed episodes and audit logs. Key from env var or key file.
  - Artifacts: src/governance/encryption.py
  - Enforcement: CI: ci.yml
  - KPI axes: Enterprise_Readiness, Authority_Modeling
  - Added: v2.1.0
- **Fairness Monitoring Adapter** (`FAIRNESS_ADAPTER`)
  - Hybrid fairness monitoring: ingests external fairness audit reports (AIF360, Fairlearn, custom) as drift signals. Three fairness drift types added to DriftType enum.
  - Artifacts: src/adapters/fairness/ingest.py, schemas/fairness_audit_v1.json, dashboard/server/models_exhaust.py
  - Enforcement: CI: ci.yml
  - KPI axes: Enterprise_Readiness, Operational_Maturity
  - Added: v2.1.0
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
- **Stale Artifact Kill-Switch** (`ARTIFACT_KILLSWITCH`)
  - Validates release artifact freshness: version match (pyproject vs VERSION.txt), current-version radar exists, badge <7 days old, history appended, contract fingerprint match.
  - Artifacts: scripts/verify_release_artifacts.py
  - Enforcement: make verify-release-artifacts, CI: ci.yml, CI: kpi.yml
  - KPI axes: Automation_Depth, Operational_Maturity
- **Banded Radar Rendering** (`BANDED_RADAR`)
  - Overlays confidence band envelope (low/high shaded polygon) on KPI radar chart using kpi_bands data.
  - Artifacts: release_kpis/radar_*_bands.png, release_kpis/radar_*_bands.svg
  - Enforcement: scripts/render_radar.py, CI: kpi.yml
  - KPI axes: All
- **KPI Eligibility CI Validation** (`KPI_ELIGIBILITY_CI`)
  - CI gate verifying every KPI has an explicit tier declaration; fails on missing, warns on unverified.
  - Artifacts: scripts/validate_kpi_eligibility.py
  - Enforcement: make validate-kpi-eligibility, CI: ci.yml
  - KPI axes: Automation_Depth, Operational_Maturity
- **CI-Eligible Benchmark** (`REAL_BENCHMARK`)
  - Deterministic re-encrypt benchmark with --ci-mode producing KPI-eligible evidence (kpi_eligible=true, evidence_level=real_workload) for scalability scoring.
  - Artifacts: release_kpis/scalability_metrics.json, release_kpis/benchmark_history.json, artifacts/benchmarks/reencrypt/benchmark_summary.json
  - Enforcement: scripts/reencrypt_benchmark.py --ci-mode, make benchmark, CI: reencrypt_benchmark.yml
  - KPI axes: Scalability, Enterprise_Readiness
- **Scalability Regression Gate** (`SCALABILITY_GATE`)
  - CI gate enforcing 80% throughput floor relative to previous benchmark and requiring real_workload evidence level.
  - Artifacts: release_kpis/SCALABILITY_GATE_REPORT.md
  - Enforcement: scripts/scalability_regression_gate.py, make scalability-gate, CI: ci.yml, CI: reencrypt_benchmark.yml
  - KPI axes: Scalability, Automation_Depth
- **Benchmark Trend Visualization** (`BENCHMARK_TREND`)
  - Throughput trend chart and markdown table from benchmark_history.json with 80% regression floor overlay.
  - Artifacts: release_kpis/benchmark_trend.png, release_kpis/benchmark_trend.svg, release_kpis/benchmark_trend.md
  - Enforcement: scripts/render_benchmark_trend.py, make benchmark-trend, CI: kpi.yml
  - KPI axes: Scalability, Operational_Maturity

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
  - Artifacts: release_kpis/tec_internal.json, release_kpis/tec_executive.json, release_kpis/tec_public_sector.json, release_kpis/TEC_SUMMARY.md
  - Enforcement: scripts/tec_ctec.py, make tec
  - KPI axes: Economic_Measurability
- **TEC Health Snapshots** (`TEC_SNAPSHOTS`)
  - Daily TEC snapshots with historical tracking for trend analysis.
  - Artifacts: release_kpis/health/history/TEC_SNAPSHOT_*.json, release_kpis/health/tec_ctec_latest.json
  - Enforcement: scripts/tec_ctec.py --snapshot
  - KPI axes: Economic_Measurability, Operational_Maturity
- **TEC Sensitivity Analysis** (`TEC_SENSITIVITY`)
  - Cost volatility index, sensitivity bands (RCF/CCF ±1 tier shift), economic fragility score, and complexity-weighted issue cost analysis.
  - Artifacts: release_kpis/tec_sensitivity.json, release_kpis/tec_sensitivity_report.md
  - Enforcement: scripts/tec_sensitivity.py, make tec-sensitivity, CI: kpi.yml
  - KPI axes: Economic_Measurability

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

### Domain Modes & Cascade Engine
Three executable domain mode modules (IntelOps, FranOps, ReflectionOps) with 36 function handlers, cross-domain cascade propagation, event contracts, and deterministic replay.

- **IntelOps Domain Mode** (`INTELOPS`)
  - Claim lifecycle automation: ingest, validate, drift detect, patch recommend, MG update, canon promote, authority check, evidence verify, triage, supersede, half-life check, confidence recalc. 12 function handlers (INTEL-F01 through INTEL-F12).
  - Artifacts: src/core/modes/intelops.py, src/core/modes/base.py
  - Enforcement: tests/test_intelops.py, make test-intelops
  - KPI axes: Technical_Completeness, Operational_Maturity
- **FranOps Domain Mode** (`FRANOPS`)
  - Canon enforcement and retcon engine: propose, bless, enforce, retcon assess/execute/propagate, inflation monitor, expire, supersede, scope check, drift detect, rollback. 12 function handlers (FRAN-F01 through FRAN-F12).
  - Artifacts: src/core/modes/franops.py, src/core/feeds/canon/workflow.py, src/core/feeds/canon/retcon_executor.py, src/core/feeds/canon/inflation_monitor.py
  - Enforcement: tests/test_franops.py, make test-franops
  - KPI axes: Technical_Completeness, Authority_Modeling
- **ReflectionOps Domain Mode** (`REFLECTIONOPS`)
  - Gate enforcement and episode lifecycle: episode begin/seal/archive, gate evaluate/degrade/killswitch, non-coercion audit, severity scoring, coherence check, reflection ingest, IRIS resolve, episode replay. 12 function handlers (RE-F01 through RE-F12).
  - Artifacts: src/core/modes/reflectionops.py, src/core/episode_state.py, src/core/severity.py, src/core/audit_log.py, src/core/killswitch.py
  - Enforcement: tests/test_reops.py, make test-reops
  - KPI axes: Technical_Completeness, Operational_Maturity
- **Cascade Engine** (`CASCADE_ENGINE`)
  - Cross-domain event propagation with 7 declarative rules: claim contradiction → canon review, claim supersede → canon update, canon retcon → episode flag, canon retcon → dependent claim invalidation, episode freeze → stale claims, killswitch → all domains freeze, red drift → auto-degrade. Depth-limited to prevent infinite loops.
  - Artifacts: src/core/modes/cascade.py, src/core/modes/cascade_rules.py
  - Enforcement: tests/test_cascade.py, make test-cascade
  - KPI axes: Technical_Completeness, Automation_Depth
- **Event Contracts & Routing Table** (`EVENT_CONTRACTS`)
  - Declarative routing table mapping 36 functions + 39 events to FEEDS topics, subtypes, handler paths, required payload fields, and emitted events. Contract validation at publish time.
  - Artifacts: src/core/feeds/contracts/routing_table.json, src/core/feeds/contracts/loader.py, src/core/feeds/contracts/validator.py
  - Enforcement: tests/test_feeds_contracts.py, make validate-contracts
  - KPI axes: Technical_Completeness, Automation_Depth
- **Canon Workflow State Machine** (`CANON_WORKFLOW`)
  - Canon entry lifecycle: PROPOSED → BLESSED → ACTIVE → UNDER_REVIEW → SUPERSEDED/RETCONNED/EXPIRED. Transition validation prevents illegal state changes.
  - Artifacts: src/core/feeds/canon/workflow.py
  - Enforcement: tests/test_franops.py
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Episode State Machine** (`EPISODE_STATE`)
  - Episode lifecycle: PENDING → ACTIVE → SEALED → ARCHIVED. Freeze support for killswitch scenarios. freeze_all() for emergency halt.
  - Artifacts: src/core/episode_state.py
  - Enforcement: tests/test_reops.py
  - KPI axes: Operational_Maturity, Technical_Completeness
- **Non-Coercion Audit Log** (`AUDIT_LOG`)
  - Append-only, hash-chained NDJSON audit log. Each entry chains to previous via SHA-256 hash. verify_chain() for tamper detection. Non-coercion attestation for every domain mode action.
  - Artifacts: src/core/audit_log.py
  - Enforcement: tests/test_reops.py
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **Domain Killswitch** (`DOMAIN_KILLSWITCH`)
  - Emergency freeze: halts all ACTIVE episodes, emits sealed halt proof with authorization details, logs to audit trail, emits drift signal on all topics.
  - Artifacts: src/core/killswitch.py
  - Enforcement: tests/test_reops.py
  - KPI axes: Operational_Maturity, Authority_Modeling
- **Severity Scorer** (`SEVERITY_SCORER`)
  - Centralized drift severity computation with drift-type weights, multi-signal aggregation, and GREEN/YELLOW/RED classification.
  - Artifacts: src/core/severity.py
  - Enforcement: tests/test_reops.py
  - KPI axes: Operational_Maturity, Technical_Completeness
- **Retcon Executor** (`RETCON_EXECUTOR`)
  - Retcon assessment (impact analysis, dependent claim enumeration) and execution (supersede chain, audit trail, drift signal emission).
  - Artifacts: src/core/feeds/canon/retcon_executor.py
  - Enforcement: tests/test_franops.py
  - KPI axes: Authority_Modeling, Technical_Completeness
- **Inflation Monitor** (`INFLATION_MONITOR`)
  - Per-domain canon health monitoring: claim count > 50, contradiction density > 10%, avg age > 30 days, supersedes depth > 5. Breaches emit canon_inflation drift signal.
  - Artifacts: src/core/feeds/canon/inflation_monitor.py
  - Enforcement: tests/test_franops.py
  - KPI axes: Operational_Maturity, Authority_Modeling
- **Money Demo v2** (`MONEY_DEMO_V2`)
  - 10-step end-to-end pipeline: LOAD → INTELOPS INGEST → VALIDATE → DELTA → FRANOPS PROPOSE → RETCON → REOPS EPISODE → CASCADE → COHERENCE → SEAL. Exercises all 3 domain modes with drift detection, retcon execution, and cascade propagation.
  - Artifacts: enterprise/src/demos/money_demo/pipeline.py, enterprise/src/demos/money_demo/fixtures/
  - Enforcement: tests/test_money_demo_v2.py, make test-money-v2
  - KPI axes: Operational_Maturity, Technical_Completeness
- **Coverage Gate** (`COVERAGE_GATE`)
  - CI gate enforcing test coverage for all 36 function handlers. Coverage matrix maps every Function ID to its test file and class.
  - Artifacts: tests/coverage_matrix.json, tests/test_coverage_gate.py
  - Enforcement: make validate-coverage
  - KPI axes: Automation_Depth, Technical_Completeness

### JRM (Judgment Refinement Module)

Log-agnostic coherence engine ingesting external telemetry (Suricata EVE, Snort fast.log, Copilot agent logs), normalizing events, running a 5-stage coherence pipeline, and outputting JRM-X packet zips. Enterprise adds cross-environment federation.

- **JRM Adapters** (`JRM_ADAPTERS`)
  - Three lossless adapters (Suricata EVE, Snort fast.log, Copilot agent) normalizing external logs into JRMEvent records with sha256 evidence hashing and malformed-line preservation.
  - Artifacts: src/core/jrm/adapters/suricata_eve.py, src/core/jrm/adapters/snort_fastlog.py, src/core/jrm/adapters/copilot_agent.py, src/core/jrm/adapters/registry.py
  - Enforcement: tests/test_jrm/test_adapters.py, CI: ci.yml
  - KPI axes: Data_Integration, Technical_Completeness
- **JRM Pipeline** (`JRM_PIPELINE`)
  - 5-stage coherence pipeline: Truth (claim clustering), Reasoning (decision lane assignment), Drift (FP_SPIKE/MISSING_MAPPING/STALE_LOGIC/ASSUMPTION_EXPIRED detection), Patch (rev++ with lineage), Memory Graph (evidence/claim/drift/patch graph + canon postures).
  - Artifacts: src/core/jrm/pipeline/truth.py, src/core/jrm/pipeline/reasoning.py, src/core/jrm/pipeline/drift.py, src/core/jrm/pipeline/patch.py, src/core/jrm/pipeline/memory_graph.py, src/core/jrm/pipeline/runner.py
  - Enforcement: tests/test_jrm/test_pipeline.py, CI: ci.yml
  - KPI axes: Technical_Completeness, Operational_Maturity
- **JRM-X Packet Builder** (`JRM_PACKET_BUILDER`)
  - Rolling packet builder producing 6-file zip output (truth_snapshot, authority_slice, decision_lineage, drift_signal, memory_graph, canon_entry + manifest) with hybrid thresholds (50k events or 25MB zip) and auto-incrementing part numbering.
  - Artifacts: src/core/jrm/packet/builder.py, src/core/jrm/packet/manifest.py, src/core/jrm/packet/naming.py
  - Enforcement: tests/test_jrm/test_packet.py, CI: ci.yml
  - KPI axes: Technical_Completeness, Data_Integration
- **JRM CLI** (`JRM_CLI`)
  - CLI commands: `coherence jrm ingest` (adapter normalize), `coherence jrm run` (pipeline execute), `coherence jrm validate` (packet verify), `coherence jrm adapters` (list available). Extension hooks for enterprise subcommands.
  - Artifacts: src/core/jrm/cli.py
  - Enforcement: tests/test_jrm/test_cli.py, CI: ci.yml
  - KPI axes: Operational_Maturity, Automation_Depth
- **JRM Schemas** (`JRM_SCHEMAS`)
  - JSON Schema Draft 2020-12 for normalized JRM events (11 required fields, sha256 evidence hash pattern) and JRM-X packet manifests (6 required file hashes, naming convention).
  - Artifacts: src/core/schemas/jrm/jrm_core.schema.json, src/core/schemas/jrm/jrm_packet.schema.json
  - Enforcement: tests/test_jrm/test_schemas.py, CI: ci.yml
  - KPI axes: Technical_Completeness, Automation_Depth
- **JRM Extension Hooks** (`JRM_HOOKS`)
  - Pluggable registries for custom drift detectors, packet validators, stream connectors, and CLI hooks. Enterprise auto-registration via hook system.
  - Artifacts: src/core/jrm/hooks/registry.py
  - Enforcement: CI: ci.yml
  - KPI axes: Data_Integration, Enterprise_Readiness
- **JRM Federation Gate** (`JRM_GATE`)
  - Packet integrity validation (manifest hash checks, required file verification), environment scope enforcement (allowlist), and field redaction (recursive field stripping with redacted zip output).
  - Artifacts: enterprise/src/deepsigma/jrm_ext/federation/gate.py
  - Enforcement: tests-enterprise/test_jrm_ext/test_gate.py
  - KPI axes: Authority_Modeling, Enterprise_Readiness
- **JRM Federation Hub** (`JRM_HUB`)
  - Multi-environment packet ingestion, cross-env drift detection (VERSION_SKEW via rev comparison, POSTURE_DIVERGENCE via confidence delta >0.3), memory graph merge, and federation report generation.
  - Artifacts: enterprise/src/deepsigma/jrm_ext/federation/hub.py
  - Enforcement: tests-enterprise/test_jrm_ext/test_hub.py
  - KPI axes: Enterprise_Readiness, Operational_Maturity
- **JRM Advisory Engine** (`JRM_ADVISORY`)
  - Cross-environment drift advisory lifecycle: publish advisories from drift detections, accept/decline with status tracking and recommendations per drift type.
  - Artifacts: enterprise/src/deepsigma/jrm_ext/federation/advisory.py
  - Enforcement: tests-enterprise/test_jrm_ext/test_advisory.py
  - KPI axes: Enterprise_Readiness, Operational_Maturity
- **JRM Packet Security** (`JRM_PACKET_SECURITY`)
  - HMAC-SHA256 manifest signing with canonical JSON, pluggable interface for KMS subclassing. Packet validator for signature verification on ingest.
  - Artifacts: enterprise/src/deepsigma/jrm_ext/security/signer.py, enterprise/src/deepsigma/jrm_ext/security/validator.py
  - Enforcement: tests-enterprise/test_jrm_ext/test_security.py
  - KPI axes: Authority_Modeling, Enterprise_Readiness

### EDGE Modules

Exportable single-file HTML applications with embedded governance — zero dependencies, offline-capable. Each module ships as a standalone `.html` file with all CSS, JS, and data inline.

- **JRM EDGE** (`JRM_EDGE`)
  - Browser-based JRM pipeline explorer. Loads Suricata/Snort/Copilot logs, runs a seeded 9-stage pipeline (RAW→PARSE→NORMALIZE→JOIN→TRUTH→REASONING→DRIFT→PATCH→MEMORY), and surfaces events, packets, health metrics, test lab, drift scoring, and policy controls. v1.0.7 adds So What panel, Analyzer/Deep Sigma view toggle, packet chain timeline with diff, stream mode with Freeze & Seal, and policy drawer with regression rerun.
  - Artifacts: edge/EDGE_JRM_EDGE_v1.0.7.html
  - Enforcement: scripts/domain_scrub.py (GPE gate)
  - KPI axes: Operational_Maturity, Enterprise_Readiness
- **RFP Co-Pilot** (`RFP_COPILOT`)
  - AI-assisted RFP extraction workflow. Structured Co-Pilot prompt extracts solicitation data into JSON; Excel Power Query loads JSON into 6 live tables (Solicitation, Key Dates, Attachments, Amendments, Risks, Open Items); role action packets assign tasks to 6 proposal team roles (Proposal Mgr, Compliance, Technical, Cost/Pricing, Contracts, Staffing). Refresh loop: amendment → rerun prompt → overwrite JSON → Refresh All.
  - Artifacts: edge/edge_rfp_copilot_excel_json.html
  - Enforcement: scripts/domain_scrub.py (GPE gate)
  - KPI axes: Enterprise_Readiness, Operational_Maturity
- **RFP Co-Pilot Exec Brief** (`RFP_COPILOT_BRIEF`)
  - 1-page executive summary of the RFP Co-Pilot workflow with Print/PDF support. Problem statement, solution flow, quick start checklist, role pull grid, and security reminder.
  - Artifacts: edge/edge_rfp_copilot_exec_brief.html
  - Enforcement: scripts/domain_scrub.py (GPE gate)
  - KPI axes: Enterprise_Readiness
- **EDGE Unified Suite** (`EDGE_UNIFIED`)
  - 8-tab unified module: Suite, Hiring, Bid, Compliance, BOE, IRIS, Delegation, Utility. Iframe-based module loading with ABP context bar.
  - Artifacts: edge/EDGE_Unified_v1.0.0.html
  - Enforcement: scripts/gate_abp.py (80 checks across 8 files)
  - KPI axes: Enterprise_Readiness, Authority_Modeling
- **Coherence Dashboard** (`EDGE_COHERENCE`)
  - 4-tab coherence overview: Overview, Claims, Drift, Analysis. Visual coherence scoring with drill-down.
  - Artifacts: edge/EDGE_Coherence_Dashboard_v2.0.0.html
  - Enforcement: scripts/gate_abp.py
  - KPI axes: Operational_Maturity, Enterprise_Readiness

- **Domino Delegation Encryption** (`DOMINO_DELEGATION`)
  - 4-of-7 Shamir threshold encryption ceremony using physical domino tiles as co-presence proof. Seven participants chain domino tiles, generate keywords (Shamir shares over GF(256)), and perform AES-256-GCM encryption/decryption with 1-hour TTL and passphrase derivation via HKDF-SHA256. Self-test gate verifies cryptographic primitives before key generation. Anti-leak UX: press-and-hold reveal, type-to-copy confirmation, clipboard overwrite.
  - Artifacts: enterprise/edge/EDGE_Domino_Delegation_Encryption.html, core/edge/EDGE_Domino_Delegation_Encryption_Verifier.html
  - Enforcement: tools/edge_lint.py (EDGE hardening gate), .github/workflows/edge_lint.yml
  - KPI axes: Enterprise_Readiness, Authority_Modeling
- **Domino Delegation Verifier** (`DOMINO_VERIFIER`)
  - Read-only ceremony record verification tool (core edition). Loads ceremony JSON, recomputes chain seal (SHA-256), validates connectivity, checks TTL status, displays session identity and keyword fingerprints. No key generation, no encryption.
  - Artifacts: core/edge/EDGE_Domino_Delegation_Encryption_Verifier.html
  - Enforcement: tools/edge_lint.py (EDGE hardening gate)
  - KPI axes: Enterprise_Readiness

## Outer-Edge Boundaries

- Not claiming full jurisdictional policy packs (EU AI Act article-by-article enforcement) yet
- Not claiming full cryptographic attestation across all pipelines and connectors yet
- Not claiming a full runtime control plane is governance (runtime is subordinate)
- Mesh federation is functional but not yet tested at production-scale WAN partitions
- Credibility engine API is tenant-scoped but not yet load-tested at multi-thousand-tenant scale
