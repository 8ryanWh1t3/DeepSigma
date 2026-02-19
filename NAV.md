---
title: "Navigation Index"
version: "1.0.0"
status: "Living Document"
last_updated: "2026-02-18"
---

# 🗺️ Navigation Index

> **What:** Complete map of every directory and key file in the repo.
>
> **So What:** Find anything in under 10 seconds. No hunting.

---

## 🚀 Onramp

| File | Purpose |
|------|---------|
| [`START_HERE.md`](START_HERE.md) | 60-second category overview + repo map |
| [`HERO_DEMO.md`](HERO_DEMO.md) | 5-minute hands-on walkthrough |
| [`README.md`](README.md) | Landing page with quick-try commands |

---

## 📜 Category (What & Why)

| File | Purpose |
|------|---------|
| [`category/declaration.md`](category/declaration.md) | Category manifesto: what Institutional Decision Infrastructure is |
| [`category/positioning.md`](category/positioning.md) | Differentiation from AI governance, MLOps, compliance |

---

## 📖 Canon (Normative Specs)

| File | Artifact |
|------|----------|
| [`canonical/prime_constitution.md`](canonical/prime_constitution.md) | System-level invariants |
| [`canonical/dlr_spec.md`](canonical/dlr_spec.md) | Decision Ledger Record (DLR) |
| [`canonical/rs_spec.md`](canonical/rs_spec.md) | Reasoning Scaffold (RS) |
| [`canonical/ds_spec.md`](canonical/ds_spec.md) | Decision Scaffold (DS) |
| [`canonical/mg_spec.md`](canonical/mg_spec.md) | Memory Graph (MG) |
| [`canonical/unified_atomic_claims_spec.md`](canonical/unified_atomic_claims_spec.md) | Atomic claims data model |

---

## 🛠 Runtime (CLI + Modules)

| Resource | Purpose |
|----------|---------|
| [`coherence_ops/`](coherence_ops/) | Python library: DLR, RS, DS, MG, Auditor, Scorer, IRIS |
| [`coherence_ops/cli.py`](coherence_ops/cli.py) | CLI entrypoint: audit, score, mg export, iris query, demo |
| [`coherence_ops/examples/`](coherence_ops/examples/) | sample_episodes.json, sample_drift.json, e2e_seal_to_report.py |
| [`engine/`](engine/) | Compression engine, degrade ladder, policy loader, supervisor |

---

## 📊 Data Model & Schemas

| Resource | Purpose |
|----------|---------|
| [`specs/`](specs/) | 12 JSON schemas (DLR, drift, episode, DTE, claim, canon, retcon, IRIS, PRIME, connector envelope) |
| [`specs/connector_contract_v1.md`](specs/connector_contract_v1.md) | Connector Contract v1.0 — standard interface + canonical envelope |
| [`connectors/`](connectors/) | Connector Contract module — `ConnectorV1` protocol + `RecordEnvelope` |
| [`llm_data_model/`](llm_data_model/) | LLM-optimized canonical data model (10 sub-directories) |
| [`rdf/`](rdf/) | RDF/SHACL ontology files |
| [`primitives/`](primitives/) | Core primitive implementations |

---

## 📋 Examples & Demo Data

| Resource | Purpose |
|----------|---------|
| [`fixtures/connectors/`](fixtures/connectors/) | **Fixture Library** — offline deterministic fixtures for all connectors |
| [`docs/fixtures.md`](docs/fixtures.md) | Fixture philosophy, structure, regeneration |
| [`tools/generate_connector_fixtures.py`](tools/generate_connector_fixtures.py) | Fixture envelope generator tool |
| [`demos/golden_path/`](demos/golden_path/) | **Golden Path** — 7-step end-to-end decision governance demo |
| [`demos/golden_path/README.md`](demos/golden_path/README.md) | Golden Path quickstart + options reference |
| [`tools/golden_path_cli.py`](tools/golden_path_cli.py) | `deepsigma golden-path` CLI entrypoint |
| [`examples/episodes/`](examples/episodes/) | 4 sealed DecisionEpisodes (success, drift, fallback, blocked) |
| [`examples/drift/`](examples/drift/) | 3 drift events (bypass, freshness, time) |
| [`examples/dte-packs/`](examples/dte-packs/) | Decision Timing Envelope examples |
| [`examples/mcp/`](examples/mcp/) | MCP integration examples |
| [`examples/demo-stack/`](examples/demo-stack/) | Demo stack configuration |
| [`examples/sample_decision_episode_001.json`](examples/sample_decision_episode_001.json) | Canonical demo episode |

---

## 📊 Dashboard

| Resource | Purpose |
|----------|---------|
| [`dashboard/`](dashboard/) | React dashboard UI + mock data + server API |
| [`dashboard/src/TrustScorecardPanel.tsx`](dashboard/src/TrustScorecardPanel.tsx) | Trust Scorecard dashboard panel |

---

## 📏 Trust & Metrics

| Resource | Purpose |
|----------|---------|
| [`specs/trust_scorecard_v1.md`](specs/trust_scorecard_v1.md) | Trust Scorecard v1.0 — metrics spec + SLO thresholds |
| [`tools/trust_scorecard.py`](tools/trust_scorecard.py) | Trust Scorecard generator (reads Golden Path output) |

---

## 📈 Diagrams

| Resource | Purpose |
|----------|---------|
| [`mermaid/`](mermaid/) | 30+ Mermaid diagrams (architecture, runtime, drift, schemas, pipelines, interop) |
| Key: [`01-system-architecture.md`](mermaid/01-system-architecture.md) | System architecture overview |
| Key: [`05-drift-to-patch.md`](mermaid/05-drift-to-patch.md) | Drift lifecycle flowchart |
| Key: [`06-coherence-ops-pipeline.md`](mermaid/06-coherence-ops-pipeline.md) | Coherence Ops pipeline |
| Key: [`30-interop-request-flow.md`](mermaid/30-interop-request-flow.md) | Interop request flow (AG-UI → A2A → MCP) |
| Key: [`31-agora-negotiation-flow.md`](mermaid/31-agora-negotiation-flow.md) | Agora negotiation → contract → runtime |

---

## 🌐 Interoperability

| Resource | Purpose |
|----------|---------|
| [`docs/interop/README.md`](docs/interop/README.md) | Interop Stack overview — AG-UI + A2A + MCP + Agora |
| [`docs/interop/COHERENCE_INTEROP_GATEWAY_SPEC_v0.1.md`](docs/interop/COHERENCE_INTEROP_GATEWAY_SPEC_v0.1.md) | Coherence Ops Interop Gateway spec v0.1 |
| [`docs/interop/DRIFT_TRIGGERS.md`](docs/interop/DRIFT_TRIGGERS.md) | Interop drift detection signals and response playbook |
| [`docs/interop/MVP_PLAN.md`](docs/interop/MVP_PLAN.md) | 2-week implementation plan with daily milestones |
| [`schemas/interop/protocol_contract.schema.json`](schemas/interop/protocol_contract.schema.json) | ProtocolContract JSON Schema |
| [`templates/interop/ProtocolContract.example.json`](templates/interop/ProtocolContract.example.json) | Example: AgentBooking ↔ AgentTravel contract |

---

## 📊 Excel-First Governance (v0.6.2+)

| Resource | Purpose |
|----------|---------|
| [`docs/excel-first/multi-dim-prompting-for-teams/README.md`](docs/excel-first/multi-dim-prompting-for-teams/README.md) | Multi-Dimensional Prompting for Teams — SharePoint-first guide |
| [`docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md`](docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md) | How BOOT!A1 initializes LLM workbook context |
| [`docs/excel-first/TABLE_SCHEMAS.md`](docs/excel-first/TABLE_SCHEMAS.md) | 7 governance table schemas with column definitions |
| [`docs/excel-first/MONEY_DEMO.md`](docs/excel-first/MONEY_DEMO.md) | Excel-first Money Demo — deterministic Drift→Patch proof |
| [`datasets/creative_director_suite/`](datasets/creative_director_suite/) | 8 CSVs — creative production sample data (25 rows each) |
| [`templates/creative_director_suite/`](templates/creative_director_suite/) | Generated Excel workbook template |
| [`tools/generate_cds_workbook.py`](tools/generate_cds_workbook.py) | Workbook generation script |
| [`tools/validate_workbook_boot.py`](tools/validate_workbook_boot.py) | BOOT contract validator (CI gate) |
| [`docs/excel-first/multi-dim-prompting-for-teams/POWER_AUTOMATE_FLOWS.md`](docs/excel-first/multi-dim-prompting-for-teams/POWER_AUTOMATE_FLOWS.md) | MDPT Power Automate flow recipes |
| [`docs/excel-first/multi-dim-prompting-for-teams/POWER_APPS_SCREEN_MAP.md`](docs/excel-first/multi-dim-prompting-for-teams/POWER_APPS_SCREEN_MAP.md) | MDPT Power Apps 5-screen layout |
| [`docs/excel-first/multi-dim-prompting-for-teams/GOVERNANCE.md`](docs/excel-first/multi-dim-prompting-for-teams/GOVERNANCE.md) | MDPT governance model — permissions, audit, compliance |

---

## 🔌 Integrations & Adapters

| Resource | Purpose |
|----------|---------|
| [`adapters/`](adapters/) | MCP, OpenClaw, OpenTelemetry adapters |
| [`docs/15-otel.md`](docs/15-otel.md) | OpenTelemetry integration guide |
| [`docs/integrations/`](docs/integrations/) | Additional integration docs |

---

## 🍳 Cookbook (Runnables)

Runnable, verifiable integration examples with expected output and failure modes.

| Resource | Purpose |
|----------|---------|
| [`cookbook/README.md`](cookbook/README.md) | Quick chooser, prerequisites, verification concept |
| [`cookbook/mcp/hello_deepsigma/`](cookbook/mcp/hello_deepsigma/) | MCP loopback — full 7-message session, run_loopback.py |
| [`cookbook/openclaw/supervised_run/`](cookbook/openclaw/supervised_run/) | Contract enforcement — PASS, BLOCKED, POSTCONDITION FAILED scenarios |
| [`cookbook/otel/trace_drift_patch/`](cookbook/otel/trace_drift_patch/) | OTel span export for episodes and drift events |
| [`cookbook/exhaust/README.md`](cookbook/exhaust/README.md) | Exhaust Inbox quick chooser — LangChain / Azure / Anthropic / manual |
| [`cookbook/exhaust/basic_ingest/`](cookbook/exhaust/basic_ingest/) | Full ingest → assemble → refine → commit cycle (no API key) |
| [`cookbook/exhaust/llm_extraction/`](cookbook/exhaust/llm_extraction/) | LLM-backed extraction demo (requires ANTHROPIC_API_KEY) |

---

## 📖 Extended Documentation

| File | Topic |
|------|-------|
| [`docs/00-vision.md`](docs/00-vision.md) | Project vision |
| [`docs/01-language-map.md`](docs/01-language-map.md) | Terminology mapping |
| [`docs/02-core-concepts.md`](docs/02-core-concepts.md) | Core concepts deep-dive |
| [`docs/05-quickstart.md`](docs/05-quickstart.md) | Original quickstart guide |
| [`docs/10-coherence-ops-integration.md`](docs/10-coherence-ops-integration.md) | Coherence Ops integration |
| [`docs/11-policy-packs.md`](docs/11-policy-packs.md) | Policy pack system |
| [`docs/12-degrade-ladder.md`](docs/12-degrade-ladder.md) | Degrade ladder |
| [`docs/13-verifiers.md`](docs/13-verifiers.md) | Verification system |
| [`docs/14-replay.md`](docs/14-replay.md) | Replay & audit trail |
| [`docs/16-run-supervised.md`](docs/16-run-supervised.md) | Supervised execution |
| [`docs/17-prompt-to-coherence-ops.md`](docs/17-prompt-to-coherence-ops.md) | Prompt engineering → Coherence Ops |
| [`docs/18-iris.md`](docs/18-iris.md) | IRIS query engine |
| [`docs/18-prime.md`](docs/18-prime.md) | PRIME threshold gates |
| [`docs/19-claim-primitive.md`](docs/19-claim-primitive.md) | Claim primitive spec |
| [`docs/20-dlr-claim-native.md`](docs/20-dlr-claim-native.md) | DLR claim-native refactor |
| [`docs/99-docs-map.md`](docs/99-docs-map.md) | De-duplication map (what to read for what) |

---

## ⚙️ Ontology & Theory

| Resource | Purpose |
|----------|---------|
| [`ontology/triad.md`](ontology/triad.md) | Truth · Reasoning · Memory formal definition |
| [`ontology/artifact_relationships.md`](ontology/artifact_relationships.md) | DLR → RS → DS → MG data flow |
| [`ontology/drift_patch_model.md`](ontology/drift_patch_model.md) | Drift detection & patch model |

---

## 🔧 Ops Pack

| Resource | Purpose |
|----------|---------|
| [`OPS_RUNBOOK.md`](OPS_RUNBOOK.md) | Run Money Demo, tests, diagnostics, incident playbooks (WHY retrieval SLO) |
| [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | Top 20 issues — symptom → cause → fix → verify |
| [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md) | CLI args, policy pack schema, environment variables |
| [`STABILITY.md`](STABILITY.md) | Stable interfaces, versioning policy, v1.0 criteria |
| [`TEST_STRATEGY.md`](TEST_STRATEGY.md) | Test tiers, SLOs, coverage, CI enforcement |

---

## ✅ Quality & Release

| Resource | Purpose |
|----------|---------|
| [`metrics/coherence_slos.md`](metrics/coherence_slos.md) | Coherence SLOs |
| [`release/CHECKLIST_v1.md`](release/CHECKLIST_v1.md) | Release readiness checklist |
| [`tests/`](tests/) | Test suite |
| [`verifiers/`](verifiers/) | Schema + logic verifiers |
| [`tools/`](tools/) | Build and validation tools |

---

## 📄 Project Files

| File | Purpose |
|------|---------|
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines |
| [`GLOSSARY.md`](GLOSSARY.md) | Full glossary of terms |
| [`SECURITY.md`](SECURITY.md) | Security policy |
| [`roadmap/README.md`](roadmap/README.md) | Quarterly roadmap |
| [`wiki/`](wiki/) | Detailed reference wiki pages |
