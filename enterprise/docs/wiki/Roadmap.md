# Roadmap

## Recently Shipped

- **v2.0.8 "Scalability Evidence + SSI Recovery"** — CI-eligible benchmark evidence for scalability KPI (5.38 → 10.0), scalability regression gate, benchmark trend visualization. SSI trajectory: 37.71 → 39.05. Issues #410-#412 closed.
- **v2.0.7 "Nonlinear Stability + Credibility Hardening"** — SSI metric, drift acceleration detection, TEC sensitivity analysis, stale artifact kill-switch, security proof pack v2, banded radar rendering, KPI eligibility tier CI validation. 392 tests, issues #314-#317 + #337-#339 closed, epics #311 + #340 closed.
- **v2.3.0 "Reference Layer"** — SDK packages (langchain-deepsigma, deepsigma-middleware, openai-deepsigma), reference layer manifesto, static demo site with GitHub Pages, coherence metrics collector, site content generation script. 433 tests, issues #477-#483 closed.
- **v2.2.0 "Mechanical Authority"** — AgentSession, authority ledger, claim trigger pipeline, coherence metrics module, FEEDS event surface (5-stage event-driven: envelope+schemas, file-bus pub/sub, manifest-first ingest, authority/evidence/triage consumers, canon store). 383 tests, issues #430-#459 (FEEDS) + #462-#476 closed.
- **v2.1.0 "Decision Infrastructure Hardening"** — Core package extraction into `src/core/`. PRIME threshold gate, CoherenceGate (GREEN/YELLOW/RED), 4D CoherenceScorer, CoherenceAuditor, Reconciler, IRIS operator query engine, DTE enforcer, schema validator, key normalization, CLI (`coherence audit|score|mg export|iris query`). Edition guard (CORE never imports ENTERPRISE). 171 tests.
- **v2.0.6** — KPI confidence bands, C-TEC pipeline, DISR dual-mode crypto, release preflight flow
- **ABP v1** — Authority Boundary Primitive: stack-independent, pre-runtime governance declaration (#419)
- **TEC/C-TEC v2** — Health pipeline + roadmap auto-sync (#391)

## v2.1.0 — Decision Infrastructure Hardening

**Gate:** All 8 KPI axes >= 7.0 (#394), SSI >= 55

Two workstreams: KPI gap closure (remaining epics) and DISR architecture.

### KPI Gap Closure

Each epic targets a single KPI axis below 7.0. Child tasks are the concrete deliverables.

**Automation Depth** (#395)

- [#401](https://github.com/8ryanWh1t3/DeepSigma/issues/401) Pre-Exec Gate Required in CI and Runtime Entry
- [#402](https://github.com/8ryanWh1t3/DeepSigma/issues/402) Idempotency/Nonce Enforcement with Replay Block
- [#403](https://github.com/8ryanWh1t3/DeepSigma/issues/403) Deterministic Replay Gate and Artifact Validation

**Economic Measurability** (#396)

- [#404](https://github.com/8ryanWh1t3/DeepSigma/issues/404) Decision Cost Ledger Schema + Emitter
- [#405](https://github.com/8ryanWh1t3/DeepSigma/issues/405) Drift-to-Patch Value Delta Calculator
- [#406](https://github.com/8ryanWh1t3/DeepSigma/issues/406) Economic KPI Ingestion Gate
- [#392](https://github.com/8ryanWh1t3/DeepSigma/issues/392) Economic Evidence Ledger

**Enterprise Readiness** (#397)

- [#407](https://github.com/8ryanWh1t3/DeepSigma/issues/407) Enterprise Deploy Sanity Workflow (docker/helm/config)
- [#408](https://github.com/8ryanWh1t3/DeepSigma/issues/408) Audit-Neutral Pack Completeness Validator
- [#409](https://github.com/8ryanWh1t3/DeepSigma/issues/409) Enterprise Operator Runbook + Release Checklist Gate

**Authority Modeling** (#399)

- [#413](https://github.com/8ryanWh1t3/DeepSigma/issues/413) Production Signature Key Custody + Verification Path
- [#414](https://github.com/8ryanWh1t3/DeepSigma/issues/414) Structural Refusal Authority Contract
- [#415](https://github.com/8ryanWh1t3/DeepSigma/issues/415) Authority Evidence Chain Export

**Technical Completeness** (#400)

- [#416](https://github.com/8ryanWh1t3/DeepSigma/issues/416) Sealed Input Snapshot + Environment Fingerprint Contract
- [#417](https://github.com/8ryanWh1t3/DeepSigma/issues/417) Intent/Decision/Evidence Schema Version Enforcement
- [#418](https://github.com/8ryanWh1t3/DeepSigma/issues/418) Replay Reproducibility Tests in CI

#### Standalone

- [#393](https://github.com/8ryanWh1t3/DeepSigma/issues/393) Evidence Source Binding Schema (Data Integration)
- [#349](https://github.com/8ryanWh1t3/DeepSigma/issues/349) Intent Mutation Detection (P2, Operational Maturity)

### DISR Architecture

- [#324](https://github.com/8ryanWh1t3/DeepSigma/issues/324) DISR Provider Interface Abstraction
- [#325](https://github.com/8ryanWh1t3/DeepSigma/issues/325) Authority-Bound Action Contracts (P0)
- [#326](https://github.com/8ryanWh1t3/DeepSigma/issues/326) Streaming Re-encrypt Engine with Checkpointing
- [#327](https://github.com/8ryanWh1t3/DeepSigma/issues/327) Signed Telemetry Event Chain

### Controls

- [#332](https://github.com/8ryanWh1t3/DeepSigma/issues/332) LOCK: v2.1.0 Scope Freeze
- [#358](https://github.com/8ryanWh1t3/DeepSigma/issues/358) MILESTONE: v2.1.0 Decision Infrastructure Hardening

## v2.1.1 — Institutional Expansion (Dormant)

Deferred until v2.1.0 gate passes. Includes adoption tooling, enterprise connectors, and DISR v2.

- [#333](https://github.com/8ryanWh1t3/DeepSigma/issues/333) EPIC: v2.1.1 Institutional Expansion
- [#334](https://github.com/8ryanWh1t3/DeepSigma/issues/334) Enterprise Connectors Suite (Jira, SharePoint, GitHub→DLR)
- [#335](https://github.com/8ryanWh1t3/DeepSigma/issues/335) DISR Provider Abstraction Layer v2
- [#318](https://github.com/8ryanWh1t3/DeepSigma/issues/318) `make try` 10-Minute Pilot Mode
- [#319](https://github.com/8ryanWh1t3/DeepSigma/issues/319) Decision Office Templates
- [#320](https://github.com/8ryanWh1t3/DeepSigma/issues/320) pilot_pack Folder
- [#321](https://github.com/8ryanWh1t3/DeepSigma/issues/321) GitHub Issues → DLR Mapping
- [#322](https://github.com/8ryanWh1t3/DeepSigma/issues/322) SharePoint / Teams Export Mode
- [#323](https://github.com/8ryanWh1t3/DeepSigma/issues/323) Jira Import/Export Adapter

## Release Proof Requirements

- Version parity across `pyproject.toml`, release notes, and KPI artifacts
- Reproducible KPI pipeline output (`release_kpis/`)
- Security gate and issue-label gate passing
- All 8 KPI axes >= 7.0 before v2.1.0 tag
