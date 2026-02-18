[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

<div align="center">

# Institutional Decision Infrastructure

**Truth · Reasoning · Memory**

[🚀 Start Here](START_HERE.md) · [🔁 Hero Demo](HERO_DEMO.md) · [🏢 Boardroom Brief](category/boardroom_brief.md) · [📜 Specs](canonical/) · [🗺️ Navigation](NAV.md) · [🔬 RAL](ABOUT.md)

</div>

---

## The Problem

Your organization makes thousands of decisions. Almost none are structurally recorded with their reasoning, evidence, or assumptions.

- **Leader leaves** → their rationale leaves with them.
- **Conditions change** → nobody detects stale assumptions.
- **Incident occurs** → root-cause analysis becomes guessing.
- **AI accelerates decisions 100×** → governance designed for human speed fails silently.

This is not a documentation gap. It is a **missing infrastructure layer**.

Every institution pays this cost — in re-litigation, audit overhead, governance drag, and silent drift. The question: keep paying in consequences, or invest in prevention.

→ [Full economic tension analysis](category/economic_tension.md) · [Boardroom brief](category/boardroom_brief.md) · [Risk model](category/risk_model.md)

---

## The Solution

**Σ OVERWATCH** fills the void between systems of record and systems of engagement with a **system of decision**.

Every decision flows through three primitives:

| Primitive | Artifact | What It Captures |
|-----------|----------|------------------|
| **Truth** | Decision Ledger Record (DLR) | What was decided, by whom, with what evidence |
| **Reasoning** | Reasoning Scaffold (RS) | Why this choice — claims, counter-claims, weights |
| **Memory** | Decision Scaffold + Memory Graph (DS + MG) | Reusable templates + queryable institutional memory |

When assumptions decay, **Drift** fires.
When drift exceeds tolerance, a **Patch** corrects it.
This is the **Drift → Patch loop** — continuous self-correction.

---

## Try It (5 Minutes)

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt

# Score coherence (0–100, A–F)
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Full pipeline: episodes → DLR → RS → DS → MG → report
python -m coherence_ops.examples.e2e_seal_to_report

# Why did we make this decision?
python -m coherence_ops iris query --type WHY --target ep-001
```

**Drift → Patch in 60 seconds** (v0.3.0):

```bash
python -m coherence_ops.examples.drift_patch_cycle
# BASELINE 90.00 (A) → DRIFT 85.75 (B) → PATCH 90.00 (A)
```

👉 Full walkthrough: [HERO_DEMO.md](HERO_DEMO.md) — 8 steps, every artifact touched.

---

## Repo Structure

```
DeepSigma/
├─ START_HERE.md          # Front door
├─ HERO_DEMO.md           # 5-min hands-on walkthrough
├─ NAV.md                 # Navigation index
├── category/             # Economic tension, boardroom brief, risk model
├── canonical/            # Normative specs: DLR, RS, DS, MG, Prime Constitution
├── coherence_ops/        # Python library + CLI + examples
├── specs/                # JSON schemas (11 schemas)
├── examples/             # Episodes, drift events, demo data
├── llm_data_model/       # LLM-optimized canonical data model
├── docs/                 # Extended docs (vision, IRIS, policy packs)
├── mermaid/              # 35+ architecture & flow diagrams
├── engine/               # Compression, degrade ladder, supervisor
├── dashboard/            # React dashboard + mock API
├── adapters/             # MCP, OpenClaw, SharePoint, Power Platform, AskSage, Snowflake, LangChain
└── release/              # Release readiness checklist
```

---

## CLI Quick Reference

| Command | Purpose |
|---------|---------|
| `python -m coherence_ops audit <path>` | Cross-artifact consistency audit |
| `python -m coherence_ops score <path> [--json]` | Coherence score (0–100, A–F) |
| `python -m coherence_ops mg export <path> --format=json` | Export Memory Graph |
| `python -m coherence_ops iris query --type WHY --target <id>` | Why was this decided? |
| `python -m coherence_ops iris query --type WHAT_DRIFTED --json` | What assumptions decayed? |
| `python -m coherence_ops demo <path>` | Score + IRIS in one command |
| `coherence reconcile <path> [--auto-fix] [--json]` | Reconcile cross-artifact inconsistencies |
| `coherence schema validate <file> --schema <name>` | Validate JSON against named schema |
| `coherence dte check <path> --dte <spec>` | Check episodes against DTE constraints |

---

## Connectors (v0.5.0)

| Connector | Transport | MCP Tools | Docs |
|-----------|-----------|-----------|------|
| SharePoint | Graph API | `sharepoint.list` / `get` / `sync` | [docs/26](docs/26-sharepoint-connector.md) |
| Power Platform | Dataverse Web API | `dataverse.list` / `get` / `query` | [docs/27](docs/27-power-platform-connector.md) |
| AskSage | REST API | `asksage.query` / `models` / `datasets` / `history` | [docs/28](docs/28-asksage-connector.md) |
| Snowflake | Cortex + SQL API | `cortex.complete` / `embed` / `snowflake.query` / `tables` / `sync` | [docs/29](docs/29-snowflake-connector.md) |
| LangChain | Callback | Governance + Exhaust handlers | [docs/23](docs/23-langgraph-adapter.md) |
| OpenClaw | HTTP | Dashboard API client | [adapters/openclaw/](adapters/openclaw/) |

---

## Key Links

| Resource | Path |
|----------|------|
| Reality Await Layer (RAL) | [ABOUT.md](ABOUT.md) |
| Front door | [START_HERE.md](START_HERE.md) |
| Hero demo | [HERO_DEMO.md](HERO_DEMO.md) |
| Boardroom brief | [category/boardroom_brief.md](category/boardroom_brief.md) |
| Economic tension | [category/economic_tension.md](category/economic_tension.md) |
| Risk model | [category/risk_model.md](category/risk_model.md) |
| Canonical specs | [/canonical/](canonical/) |
| JSON schemas | [/specs/](specs/) |
| Python library | [/coherence_ops/](coherence_ops/) |
| IRIS docs | [docs/18-iris.md](docs/18-iris.md) |
| Docs map | [docs/99-docs-map.md](docs/99-docs-map.md) |

---

## Operations

| Resource | Purpose |
|----------|---------|
| [OPS_RUNBOOK.md](OPS_RUNBOOK.md) | Run Money Demo, tests, diagnostics, incident playbooks |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Top 20 issues — symptom → cause → fix → verify |
| [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) | All CLI args, policy pack schema, environment variables |
| [STABILITY.md](STABILITY.md) | What's stable, what's not, versioning policy, v1.0 criteria |
| [TEST_STRATEGY.md](TEST_STRATEGY.md) | Test tiers, SLOs, how to run locally, coverage |

**Run with coverage:**
```bash
pytest --cov=coherence_ops --cov-report=term-missing
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions must maintain consistency with Truth · Reasoning · Memory and the four canonical artifacts (DLR / RS / DS / MG).

## License

See [LICENSE](LICENSE).

---

<div align="center">

**Σ OVERWATCH**
*We don't sell agents. We sell the ability to trust them.*

</div>
