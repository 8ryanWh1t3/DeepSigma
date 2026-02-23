# Roadmap Grouping (Issues)

## v2.0.7
### EPICs (2)
- #311 **EPIC: v2.0.7 Credibility Hardening (Stark)**  
  labels: kpi:operational_maturity, sev:P1, type:feature, lane:epic, roadmap, stark, v2.0.7
- #340 **EPIC: v2.0.7 Nonlinear Stability Layer**  
  labels: roadmap, v2.0.7, epic, stability

### ISSUEs (7)
- #314 **v2.0.7: Radar Confidence Bands**  
  labels: priority:P1, kpi:economic_measurability, sev:P1, type:feature, roadmap, v2.0.7, credibility
- #315 **v2.0.7: KPI Eligibility Tiers (Simulated/Real/Production)**  
  labels: priority:P1, kpi:automation_depth, sev:P1, type:feature, roadmap, v2.0.7, credibility
- #316 **v2.0.7: Stale Artifact Kill-Switch**  
  labels: priority:P0, kpi:automation_depth, sev:P0, type:feature, roadmap, v2.0.7, ci
- #317 **v2.0.7: Security Posture Proof Pack v2**  
  labels: priority:P1, kpi:operational_maturity, sev:P1, type:feature, roadmap, v2.0.7, security
- #337 **v2.0.7: System Stability Index (SSI) Metric**  
  labels: roadmap, v2.0.7, metrics, stability
- #338 **v2.0.7: Drift Acceleration Detection Engine**  
  labels: roadmap, v2.0.7, metrics, drift
- #339 **v2.0.7: TEC Sensitivity & Variance Modeling**  
  labels: roadmap, v2.0.7, metrics, tec

## v2.1.0
### EPICs (2)
- #313 **EPIC: v2.1.0 DISR Architecture Expansion (Stark)**  
  labels: kpi:authority_modeling, sev:P1, type:feature, lane:epic, roadmap, stark, v2.1.0
- #342 **EPIC: Close the 4 Gaps (Determinism + Intent + Audit-Neutral Logic + Pre-Exec Accountability)**  
  labels: kpi:operational_maturity, sev:P1, type:feature, roadmap, v2.1.0, governance, epic, hardening

### ISSUEs (20)
- #324 **v2.1.0: DISR Provider Interface Abstraction**  
  labels: priority:P1, kpi:technical_completeness, sev:P1, type:feature, roadmap, v2.1.0, architecture
- #325 **v2.1.0: Authority-Bound Action Contracts**  
  labels: priority:P0, kpi:authority_modeling, sev:P0, type:feature, roadmap, v2.1.0, architecture, security
- #326 **v2.1.0: Streaming Re-encrypt Engine with Checkpointing**  
  labels: priority:P1, kpi:scalability, sev:P1, type:feature, roadmap, v2.1.0, architecture
- #327 **v2.1.0: Signed Telemetry Event Chain**  
  labels: priority:P1, kpi:operational_maturity, sev:P1, type:feature, roadmap, v2.1.0, security
- #332 **LOCK: v2.1.0 Scope Freeze**  
  labels: v2.1.0, release, governance
- #343 **GAP: Deterministic Replay Spec (What must be sealed to replay?)**  
  labels: kpi:operational_maturity, sev:P1, type:doc, roadmap, v2.1.0, governance, hardening
- #344 **GAP: Sealed Input State Snapshot (pre-run) + provenance bundle**  
  labels: kpi:technical_completeness, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #345 **GAP: Deterministic Environment Fingerprint (runtime + dependencies)**  
  labels: kpi:technical_completeness, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #346 **GAP: Replay Runner (one-command) to reproduce last run from sealed artifacts**  
  labels: kpi:enterprise_readiness, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #347 **GAP: Intent Packet schema (intent -> scope -> risk -> success criteria)**  
  labels: kpi:authority_modeling, sev:P1, type:doc, roadmap, v2.1.0, governance, hardening
- #348 **GAP: Intent Hash Binding (intent hash must match action contract before execution)**  
  labels: kpi:authority_modeling, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #349 **GAP: Intent Mutation Detection (diff + alert if intent changes after approval)**  
  labels: kpi:operational_maturity, sev:P2, type:feature, roadmap, v2.1.0, governance, hardening
- #350 **GAP: Decision Invariants Ledger (PRIME-like invariants for decisions)**  
  labels: kpi:operational_maturity, sev:P1, type:doc, roadmap, v2.1.0, governance, hardening
- #351 **GAP: Claim->Evidence->Authority binding model (machine-checkable)**  
  labels: kpi:technical_completeness, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #352 **GAP: Audit-Neutral Output Pack (context-free review bundle)**  
  labels: kpi:enterprise_readiness, sev:P2, type:feature, roadmap, v2.1.0, governance, hardening
- #353 **GAP: Pre-Execution Gate (block execution unless Intent + Authority + Policy satisfied)**  
  labels: kpi:automation_depth, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #354 **GAP: Authority Signature Verification (remove placeholder signing)**  
  labels: kpi:authority_modeling, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #355 **GAP: Replay/Nonce Protection Enforcement (prevent repeat execution without idempotency key)**  
  labels: kpi:automation_depth, sev:P2, type:feature, roadmap, v2.1.0, governance, hardening
- #356 **GAP: Decision Episode sealing (post-run binds outcome to intent+authority+inputs)**  
  labels: kpi:operational_maturity, sev:P1, type:feature, roadmap, v2.1.0, governance, hardening
- #358 **MILESTONE: v2.1.0 Decision Infrastructure Hardening**  
  labels: v2.1.0, hardening, milestone

## v2.1.1
### EPICs (2)
- #312 **EPIC: v2.0.8 Adoption + Enterprise Integration Wedge (Stark)**  
  labels: kpi:enterprise_readiness, sev:P1, type:feature, lane:epic, roadmap, stark, v2.0.8, v2.1.0-pre, v2.1.1
- #333 **EPIC: v2.1.1 Institutional Expansion**  
  labels: roadmap, epic, dormant, v2.1.1

### ISSUEs (8)
- #318 **v2.0.8: make try (10-Minute Pilot Mode)**  
  labels: priority:P1, kpi:enterprise_readiness, sev:P1, type:feature, roadmap, v2.0.8, adoption, v2.1.1
- #319 **v2.0.8: Decision Office Templates**  
  labels: priority:P1, kpi:technical_completeness, sev:P1, type:feature, roadmap, v2.0.8, adoption, v2.1.1
- #320 **v2.0.8: pilot_pack Folder**  
  labels: priority:P1, kpi:enterprise_readiness, sev:P1, type:feature, roadmap, v2.0.8, adoption, v2.1.1
- #321 **v2.1.0-pre: GitHub Issues → DLR Mapping**  
  labels: priority:P1, kpi:data_integration, sev:P1, type:feature, roadmap, v2.1.0-pre, integration, v2.1.1
- #322 **v2.1.0-pre: SharePoint / Teams Export Mode**  
  labels: priority:P1, kpi:data_integration, sev:P1, type:feature, roadmap, v2.1.0-pre, integration, v2.1.1
- #323 **v2.1.0-pre: Jira Import/Export Adapter**  
  labels: priority:P2, kpi:data_integration, sev:P2, type:feature, roadmap, v2.1.0-pre, integration, v2.1.1
- #334 **v2.1.1: Enterprise Connectors Suite**  
  labels: roadmap, integration, dormant, v2.1.1
- #335 **v2.1.1: DISR Provider Abstraction Layer v2**  
  labels: roadmap, security, dormant, v2.1.1

## UNVERSIONED
### EPICs (5)
- #148 **Epic: Helm chart + Kubernetes manifests**  
  labels: infra, priority:P1, kpi:automation_depth, sev:P1, type:feature
- #149 **Epic: Multi-region mesh over real networks**  
  labels: mesh, scale, priority:P1, kpi:scalability, sev:P2, type:feature
- #152 **Epic: Horizontal scaling (stateless API + shared persistence)**  
  labels: scale, priority:P1, kpi:scalability, sev:P2, type:feature
- #279 **EPIC: v2.1.0 Dual-Mode DISR Architecture (Local default + optional KMS)**  
  labels: kpi:operational_maturity, sev:P1, type:feature, lane:epic
- #280 **EPIC: v2.0.5 DISR Pilot Wedge (10-minute recoverability proof)**  
  labels: kpi:enterprise_readiness, sev:P2, type:feature, lane:epic

### ISSUEs (121)
- #1 **run_supervised.py output does not conform to episode.schema.json**  
  labels: bug, schema
- #2 **Drift events from run_supervised.py do not conform to drift.schema.json**  
  labels: bug, schema
- #3 **Add unit test suite with pytest**  
  labels: enhancement, infra
- #4 **Add GitHub Actions CI pipeline**  
  labels: enhancement, infra
- #5 **Expand validate_examples.py coverage to all artifact types**  
  labels: enhancement, good first issue, schema
- #6 **Implement OpenTelemetry reference exporter**  
  labels: enhancement, adapter
- #7 **Implement OpenClaw adapter**  
  labels: enhancement, adapter
- #8 **MCP server: implement full handshake and capabilities**  
  labels: enhancement, adapter
- #9 **Drift to Patch automation CLI tool**  
  labels: enhancement
- #10 **Verify policy pack hash at load time**  
  labels: enhancement, good first issue
- #11 **Dashboard: support real episode and drift data ingestion**  
  labels: enhancement
- #12 **Enhance replay harness to re-run degrade ladder logic**  
  labels: enhancement
- #13 **Implement CoherenceOps framework (DLR/RS/DS/MG)**  
  labels: enhancement
- #14 **Build LLM Data Model folder with canonical record envelope**  
  labels: enhancement
- #15 **Create Mermaid architectural diagrams for entire repo**  
  labels: documentation
- #16 **Build comprehensive Wiki documentation (47+ pages)**  
  labels: documentation
- #17 **Add unit tests for coherence_ops package**  
  labels: enhancement
- #18 **Add Metric record type example to LLM Data Model**  
  labels: enhancement
- #19 **Dashboard: add CoherenceOps and LLM Data Model panels**  
  labels: enhancement
- #20 **Integrate LLM Data Model validation into CI pipeline**  
  labels: enhancement, infra
- #21 **Add REST API endpoints for CoherenceOps and LLM Data Model**  
  labels: enhancement
- #22 **Update repo README to reference coherence_ops, llm_data_model, and mermaid folders**  
  labels: documentation
- #23 **Add CLI, end-to-end examples, and demo command to coherence_ops**  
  labels: enhancement
- #24 **Fix: policy pack hash, LLM example IDs, missing logo, deprecated RefResolver, PYTHONPATH**  
  labels: bug
- #30 **[Category] README rewrite — Institutional Decision Infrastructure declaration**  
  labels: 
- #31 **[Canonical] Create spec pack — DLR, RS, DS, MG, Unified Atomic Claims, Prime Constitution**  
  labels: 
- #32 **[Demo] End-to-end demo loop — Decision → Seal → Drift → Patch → Memory**  
  labels: 
- #33 **[Runtime] Create operational runbooks — drift-patch workflow, sealing protocol, encode episode**  
  labels: 
- #34 **[Category] Create category directory — declaration and positioning**  
  labels: 
- #35 **[Ontology] Create ontology directory — triad, artifact relationships, drift-patch model**  
  labels: 
- #36 **[Metrics] Define Coherence SLOs — measurable quality bar for decision infrastructure**  
  labels: 
- #37 **[Roadmap] Create quarterly roadmap with milestones**  
  labels: 
- #38 **[Quality] Audit all new docs for consistent versioning headers and YAML frontmatter**  
  labels: 
- #39 **[Quality] Validate sample_decision_episode_001.json against existing JSON schemas**  
  labels: 
- #87 **Ship Game Studio Lattice vertical example**  
  labels: enhancement, vertical-pack
- #88 **Harden MCP adapter with retry + circuit-breaker**  
  labels: enhancement, adapter
- #89 **Stabilize OTel span naming and attribute conventions**  
  labels: enhancement, infra
- #90 **Add second vertical example (Healthcare or FinServ)**  
  labels: enhancement, vertical-pack
- #91 **Expand CI matrix: add Windows runner + Python 3.13**  
  labels: enhancement, infra
- #92 **Wire dashboard to live Trust Scorecard data**  
  labels: enhancement
- #93 **Production-harden SharePoint connector with Azure AD auth**  
  labels: enhancement, connector
- #94 **Add Snowflake connector with contract compliance**  
  labels: enhancement, connector
- #95 **Add LangGraph connector for LLM chain evidence**  
  labels: enhancement, connector
- #96 **Harden exhaust pipeline for production throughput**  
  labels: enhancement, scale
- #97 **Ship MDPT Power App deployment package**  
  labels: enhancement, excel-first
- #98 **Add Healthcare and FinServ Excel-first workbook templates**  
  labels: vertical-pack, excel-first
- #99 **Benchmark mesh topology at 100+ nodes**  
  labels: mesh, scale
- #100 **Implement JSONL compaction for evidence archives**  
  labels: enhancement, scale
- #101 **Implement hot/warm/cold evidence tiering**  
  labels: credibility-engine, scale
- #102 **Multi-region sync plane prototype**  
  labels: credibility-engine, scale
- #103 **Optimize CI pipeline: parallel jobs + caching**  
  labels: enhancement, infra
- #104 **Add PostgreSQL/SQLite persistence backend**  
  labels: enhancement, scale
- #105 **Implement real HTTP mesh transport layer**  
  labels: enhancement, mesh
- #106 **Ship production MCP server with tool registry**  
  labels: enhancement, adapter
- #107 **Add webhook notification system for drift events**  
  labels: enhancement
- #108 **Harden OpenClaw WASM runtime for untrusted policies**  
  labels: enhancement
- #109 **Add RDF/SPARQL service for semantic lattice queries**  
  labels: enhancement
- #133 **One-command Money Demo**  
  labels: examples, priority:P1, kpi:economic_measurability, sev:P1, type:feature
- #134 **Dependency lock + deterministic install**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:debt
- #135 **Golden-path proof artifacts in README**  
  labels: docs, priority:P1, kpi:operational_maturity, sev:P1, type:doc
- #136 **Connector safety + data boundary documentation**  
  labels: connector, docs, priority:P1, kpi:data_integration, sev:P1, type:doc
- #137 **CI release hygiene: test + lint + tag → artifacts**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:debt
- #138 **SDK quickstart: first lattice in 5 minutes**  
  labels: docs, priority:P2, kpi:operational_maturity, sev:P2, type:doc
- #139 **Auto-generated API reference from OpenAPI spec**  
  labels: docs, priority:P2, kpi:operational_maturity, sev:P2, type:doc
- #140 **Connector plugin SDK + custom connector guide**  
  labels: connector, docs, priority:P1, kpi:data_integration, sev:P1, type:feature
- #141 **Devcontainer + GitHub Codespaces config**  
  labels: infra, priority:P2, kpi:automation_depth, sev:P2, type:feature
- #142 **Example: custom OpenClaw policy module with tests**  
  labels: adapter, examples, priority:P2, kpi:economic_measurability, sev:P2, type:feature
- #143 **Prometheus metrics + Grafana dashboard template**  
  labels: infra, priority:P1, kpi:automation_depth, sev:P1, type:feature
- #144 **Automated golden path proof regeneration in CI**  
  labels: infra, priority:P1, kpi:automation_depth, sev:P1, type:feature
- #145 **Data retention automation: TTL purge + compaction cron**  
  labels: scale, priority:P1, kpi:scalability, sev:P1, type:feature
- #146 **Compliance report generator: SOC 2 evidence export**  
  labels: docs, priority:P1, kpi:enterprise_readiness, sev:P1, type:feature
- #147 **Envelope-level encryption for evidence at rest**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:feature
- #150 **Signed releases with Sigstore + SBOM**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:feature
- #151 **Publish to PyPI + GHCR on tagged release**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:feature
- #160 **Add Power Automate flow templates (JSON)**  
  labels: enhancement
- #161 **Add Python validator for CSV/schema**  
  labels: enhancement
- #162 **Add exporter: workbook → JSON sealed snapshot**  
  labels: enhancement
- #163 **Add dashboard charts (Excel) for trends**  
  labels: enhancement
- #164 **Add governance: ownership + review cadence policy**  
  labels: enhancement
- #165 **Add JSON-output variants for canonical prompts (automation)**  
  labels: enhancement
- #166 **Add Decision Compression prompt variant**  
  labels: enhancement
- #167 **Add prompt health telemetry (usage + drift flags) tied to PromptLibraryTable**  
  labels: enhancement
- #186 **Release Pipeline Epic: CI, signing, publish, and proof**  
  labels: infra, priority:P0, kpi:automation_depth, sev:P0, type:feature
- #187 **Helm chart split: core workloads and ingress**  
  labels: infra, priority:P1, kpi:enterprise_readiness, sev:P1, type:feature
- #188 **Helm chart split: optional Fuseki and ServiceMonitor**  
  labels: infra, priority:P1, kpi:enterprise_readiness, sev:P1, type:feature
- #189 **Helm chart split: HPA and production overlays**  
  labels: infra, scale, priority:P1, kpi:scalability, sev:P2, type:feature
- #190 **Helm chart split: install validation and helm test**  
  labels: infra, priority:P1, kpi:automation_depth, sev:P1, type:feature
- #191 **Mesh split: peer identity and mTLS**  
  labels: infra, mesh, priority:P1, kpi:scalability, sev:P2, type:feature
- #192 **Mesh split: partition detection and recovery**  
  labels: mesh, scale, priority:P1, kpi:scalability, sev:P2, type:feature
- #193 **Mesh split: anti-entropy and delta sync**  
  labels: mesh, scale, priority:P1, kpi:scalability, sev:P2, type:feature
- #194 **Mesh split: WAN integration tests and topology visibility**  
  labels: infra, mesh, priority:P1, kpi:scalability, sev:P2, type:feature
- #195 **Stateless API split: remove in-memory runtime state**  
  labels: infra, scale, priority:P1, kpi:scalability, sev:P1, type:feature
- #196 **Stateless API split: health degradation and graceful shutdown**  
  labels: infra, priority:P1, kpi:enterprise_readiness, sev:P1, type:feature
- #197 **Stateless API split: load testing and scaling guide**  
  labels: scale, priority:P1, kpi:scalability, sev:P1, type:feature
- #199 **Pilot Results: PASS→FAIL→PASS, branch gate enabled, final user validation pending**  
  labels: infra, docs, priority:P1, kpi:automation_depth, sev:P1, type:doc
- #254 **DISR: Bind key rotation to Authority Ledger (DRI approval + signed rotation event)**  
  labels: kpi:authority_modeling, sev:P1, type:feature
- #255 **DISR: Add reencrypt benchmark (100k records / 1GB dataset) with resource telemetry**  
  labels: kpi:scalability, sev:P1, type:feature
- #256 **DISR: Add quantified security metrics (MTTR + Reencrypt Throughput) to 10-min demo**  
  labels: kpi:economic_measurability, sev:P1, type:feature
- #257 **DISR: Security spec + key lifecycle docs (Breakable/Detectable/Rotatable/Recoverable)**  
  labels: kpi:enterprise_readiness, sev:P1, type:doc
- #258 **DISR: Add security_gate.yml (blocks PRs on crypto misuse + missing envelope fields)**  
  labels: kpi:automation_depth, sev:P1, type:feature
- #259 **DISR: Add recovery drill to pilot workflow (reencrypt dry-run + rollback narrative)**  
  labels: kpi:operational_maturity, sev:P1, type:doc
- #260 **DISR: Standardize crypto envelope metadata (key_id, key_version, alg, nonce, aad)**  
  labels: kpi:data_integration, sev:P1, type:feature
- #261 **DISR: Implement Keyring + TTL model (key_id, versions, expires_at, status)**  
  labels: kpi:technical_completeness, sev:P1, type:feature
- #262 **DISR: Add rotate_keys command (automatic rotation + audit events)**  
  labels: kpi:technical_completeness, sev:P1, type:feature
- #263 **DISR: Add reencrypt job (old key -> new key) with checkpointing + rollback plan**  
  labels: kpi:operational_maturity, sev:P1, type:feature
- #264 **DISR: Add crypto_misuse_scan.py (nonce reuse, missing key_id, weak randomness, AAD omissions)**  
  labels: kpi:automation_depth, sev:P1, type:feature
- #265 **DISR: Emit sealed security events (KEY_ROTATED, NONCE_REUSE_DETECTED, REENCRYPT_COMPLETED)**  
  labels: kpi:operational_maturity, sev:P2, type:feature
- #266 **DISR: Add unit tests for keyring + rotation + reencrypt pipeline**  
  labels: kpi:technical_completeness, sev:P1, type:debt
- #267 **DISR: Write "10-minute security demo" quickstart (breakable/detectable/rotatable/recoverable)**  
  labels: kpi:enterprise_readiness, sev:P1, type:doc
- #268 **DISR: Wire security artifacts into pilot_pack + README surface area**  
  labels: kpi:enterprise_readiness, sev:P1, type:feature
- #281 **DISR-210: Define CryptoProvider interface + provider registry (dual-mode)**  
  labels: kpi:technical_completeness, sev:P1, type:feature, lane:provider-layer
- #282 **DISR-210: LocalKeyStoreProvider (default) + envelope v1**  
  labels: kpi:data_integration, sev:P1, type:feature, lane:provider-layer
- #283 **DISR-210: Optional KMSProvider stubs (AWS/GCP/Azure) behind same interface**  
  labels: kpi:enterprise_readiness, sev:P2, type:feature, lane:provider-layer
- #284 **DISR-210: Authority Action Contract for rotate/reencrypt (signed + DRI-bound)**  
  labels: kpi:authority_modeling, sev:P1, type:feature, lane:authority
- #285 **DISR-210: Authority Ledger v1 (versioned snapshots + precedence rules)**  
  labels: kpi:authority_modeling, sev:P1, type:feature, lane:authority
- #286 **DISR-210: Sealed security events (KEY_ROTATED, NONCE_REUSE, REENCRYPT_DONE, PROVIDER_CHANGED)**  
  labels: kpi:operational_maturity, sev:P1, type:feature, lane:telemetry
- #287 **DISR-210: Crypto policy engine (provider/alg selection + constraints) + envelope v2 plan**  
  labels: kpi:data_integration, sev:P1, type:feature, lane:policy
- #288 **DISR-210: Streaming/batched reencrypt pipeline (idempotent + checkpoint/resume)**  
  labels: kpi:scalability, sev:P1, type:feature, lane:recovery-scale
- #289 **DISR-210: Benchmark suite (regression) for MTTR + throughput + CPU/RAM**  
  labels: kpi:economic_measurability, sev:P1, type:feature, lane:benchmarks
- #290 **DISR-210: Extend security gate (policy violations + provider drift + envelope version checks)**  
  labels: kpi:automation_depth, sev:P1, type:feature, lane:automation-gate
- #291 **DISR-210: Security Audit Pack export (sealed events + authority ledger + metrics + configs)**  
  labels: kpi:enterprise_readiness, sev:P1, type:feature, lane:audit-pack
