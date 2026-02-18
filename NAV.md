---
title: "Navigation Index"
version: "1.0.0"
status: "Living Document"
last_updated: "2026-02-16"
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
| [`specs/`](specs/) | 11 JSON schemas (DLR, drift, episode, DTE, claim, canon, retcon, IRIS, PRIME) |
| [`llm_data_model/`](llm_data_model/) | LLM-optimized canonical data model (10 sub-directories) |
| [`rdf/`](rdf/) | RDF/SHACL ontology files |
| [`primitives/`](primitives/) | Core primitive implementations |

---

## 📋 Examples & Demo Data

| Resource | Purpose |
|----------|---------|
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

---

## 📈 Diagrams

| Resource | Purpose |
|----------|---------|
| [`mermaid/`](mermaid/) | 28+ Mermaid diagrams (architecture, runtime, drift, schemas, pipelines) |
| Key: [`01-system-architecture.md`](mermaid/01-system-architecture.md) | System architecture overview |
| Key: [`05-drift-to-patch.md`](mermaid/05-drift-to-patch.md) | Drift lifecycle flowchart |
| Key: [`06-coherence-ops-pipeline.md`](mermaid/06-coherence-ops-pipeline.md) | Coherence Ops pipeline |

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
